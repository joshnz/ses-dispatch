import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from dispatch.models import Job, Crew, Assignment
from dispatch.services.queue import (
    queue_job_for_crew, promote_next_job,
    reorder_queue as do_reorder_queue,
    remove_from_queue as do_remove_from_queue,
)
from dispatch.views.sse import notify_dispatch_change

logger = logging.getLogger(__name__)


@login_required
@require_POST
def dispatch_crew(request):
    job = get_object_or_404(Job, pk=request.POST["job_id"])
    crew = get_object_or_404(Crew, pk=request.POST["crew_id"], status="available")

    if job.status not in ("pending", "assigned"):
        return HttpResponseBadRequest("Job cannot be dispatched to")

    if job.status == "assigned" and not request.POST.get("confirmed"):
        existing_crews = Crew.objects.filter(current_job=job)
        existing_names = ", ".join(c.callsign for c in existing_crews)
        return render(request,
            "dispatch/partials/confirm_multi_dispatch_modal.html", {
                "job": job,
                "new_crew": crew,
                "existing_crew_names": existing_names,
            })

    is_additional = job.status == "assigned"

    if job.status == "pending":
        job.status = "assigned"
        job.assigned_at = timezone.now()
        job.save()

    crew.status = "dispatched"
    crew.current_job = job
    crew.deployed_at = crew.deployed_at or timezone.now()
    crew.save()

    Assignment.objects.create(
        job=job, crew=crew,
        dispatched_by=request.user,
        is_additional=is_additional,
        notes=f"{'Additional d' if is_additional else 'D'}ispatched: {crew.callsign}",
    )

    notify_dispatch_change()
    return render(request, "dispatch/partials/crew_card.html", {"crew": crew})


@login_required
@require_POST
def complete_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    job.status = "completed"
    job.completed_at = timezone.now()
    job.save()

    assigned_crews = list(Crew.objects.filter(current_job=job))
    freed_names = []

    for crew in assigned_crews:
        next_entry = promote_next_job(crew)

        if next_entry:
            crew.status = "dispatched"
            crew.current_job = next_entry.job
            crew.deployed_at = timezone.now()
            crew.save()

            next_entry.job.status = "assigned"
            next_entry.job.assigned_at = timezone.now()
            next_entry.job.save()

            Assignment.objects.create(
                job=next_entry.job, crew=crew,
                dispatched_by=request.user,
                notes=f"Auto-dispatched from queue (was on {job.sierra_number})",
            )

            freed_names.append(
                f"{crew.callsign} -> {next_entry.job.sierra_number}"
            )
        else:
            crew.status = "available"
            crew.current_job = None
            crew.speed_kmh = 0
            crew.save()
            freed_names.append(f"{crew.callsign} (available)")

    Assignment.objects.filter(
        job=job, completed_at__isnull=True
    ).update(completed_at=timezone.now())

    notify_dispatch_change()
    messages.success(request,
        f"Job {job.sierra_number} completed. {', '.join(freed_names)}"
    )
    return redirect("dashboard")


@login_required
@require_POST
def cancel_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    job.status = "cancelled"
    job.save()

    assigned_crews = Crew.objects.filter(current_job=job)
    assigned_crews.update(status="available", current_job=None, speed_kmh=0)

    notify_dispatch_change()
    messages.info(request, f"Job {job.sierra_number} cancelled.")
    return redirect("dashboard")


@login_required
@require_POST
def on_scene(request, crew_id):
    crew = get_object_or_404(Crew, pk=crew_id)
    crew.status = "on_scene"
    crew.speed_kmh = 0
    crew.save()

    if crew.current_job:
        crew.current_job.status = "on_scene"
        crew.current_job.save()

        Assignment.objects.filter(
            crew=crew, job=crew.current_job, arrived_at__isnull=True
        ).update(arrived_at=timezone.now())

    notify_dispatch_change()
    return render(request, "dispatch/partials/crew_card.html", {"crew": crew})


@login_required
@require_POST
def return_to_base(request, crew_id):
    crew = get_object_or_404(Crew, pk=crew_id)
    mode = request.POST.get("mode", "")

    # If crew has a current job and no mode specified, show the modal
    if crew.current_job and not mode:
        return render(request, "dispatch/partials/return_to_base_modal.html", {
            "crew": crew,
        })

    if mode == "complete" and crew.current_job:
        job = crew.current_job
        job.status = "completed"
        job.completed_at = timezone.now()
        job.save()

        Assignment.objects.filter(
            job=job, completed_at__isnull=True
        ).update(completed_at=timezone.now())

        # Free other crews assigned to this job
        for other_crew in Crew.objects.filter(current_job=job).exclude(pk=crew.pk):
            next_entry = promote_next_job(other_crew)
            if next_entry:
                other_crew.status = "dispatched"
                other_crew.current_job = next_entry.job
                other_crew.deployed_at = timezone.now()
                other_crew.save()
                next_entry.job.status = "assigned"
                next_entry.job.assigned_at = timezone.now()
                next_entry.job.save()
                Assignment.objects.create(
                    job=next_entry.job, crew=other_crew,
                    dispatched_by=request.user,
                    notes=f"Auto-dispatched from queue (was on {job.sierra_number})",
                )
            else:
                other_crew.status = "available"
                other_crew.current_job = None
                other_crew.speed_kmh = 0
                other_crew.save()

    elif mode == "pending" and crew.current_job:
        job = crew.current_job
        # Check if other crews are still assigned
        other_assigned = Crew.objects.filter(current_job=job).exclude(pk=crew.pk)
        if not other_assigned.exists():
            job.status = "pending"
            job.assigned_at = None
            job.save()

        Assignment.objects.filter(
            crew=crew, job=job, completed_at__isnull=True
        ).update(completed_at=timezone.now(), notes="Returned to base - job returned to pending")

    # Clear crew's current job and queue entry, mark as returning
    from dispatch.models import CrewJobQueue
    CrewJobQueue.objects.filter(crew=crew, position=0).delete()
    crew.status = "returning"
    crew.current_job = None
    crew.save()

    notify_dispatch_change()
    return render(request, "dispatch/partials/crew_card.html", {"crew": crew})


@login_required
@require_POST
def toggle_crew(request, crew_id):
    crew = get_object_or_404(Crew, pk=crew_id)
    if crew.status == "offline":
        crew.status = "available"
    elif crew.status == "available":
        crew.status = "offline"
    crew.save()

    notify_dispatch_change()
    return render(request, "dispatch/partials/crew_card.html", {"crew": crew})


@login_required
@require_POST
def send_upload_link(request, job_id):
    from uploads.models import UploadToken
    from datetime import timedelta
    from django.http import HttpResponse

    job = get_object_or_404(Job, pk=job_id)
    token = UploadToken.objects.create(
        job=job, expires_at=timezone.now() + timedelta(hours=24)
    )

    upload_url = request.build_absolute_uri(f"/upload/{token.token}/")

    sms_sent = False
    if getattr(request, "settings", None) and getattr(request.settings, "TWILIO_ENABLED", False):
        from twilio.rest import Client
        from django.conf import settings
        client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
        client.messages.create(
            body=f"VicSES: Upload photos at {job.location_address}. Link: {upload_url}",
            from_=settings.TWILIO_FROM_NUMBER,
            to=job.caller_phone.replace(" ", ""),
        )
        sms_sent = True

    logger.info("Upload link for %s: %s", job.sierra_number, upload_url)

    html = (
        '<div class="alert alert-success mt-2">'
        f'<strong>Upload link generated for {job.sierra_number}</strong><br>'
    )
    if sms_sent:
        html += f'<small>SMS sent to {job.caller_phone}</small><br>'
    html += (
        f'<input type="text" class="form-control form-control-sm mt-1" '
        f'value="{upload_url}" readonly onclick="this.select()">'
        '<small class="text-muted">Click to select, then copy</small>'
        '</div>'
    )
    return HttpResponse(html)


@login_required
@require_POST
def add_to_queue(request, crew_id):
    crew = get_object_or_404(Crew, pk=crew_id)
    job = get_object_or_404(Job, pk=request.POST["job_id"])
    position = request.POST.get("position")
    position = int(position) if position else None

    queue_job_for_crew(crew, job, position=position, user=request.user)
    notify_dispatch_change()

    return render(request, "dispatch/partials/crew_card.html", {"crew": crew})


@login_required
@require_http_methods(["POST", "DELETE"])
def remove_from_queue_view(request, crew_id, job_id):
    crew = get_object_or_404(Crew, pk=crew_id)
    job = get_object_or_404(Job, pk=job_id)
    do_remove_from_queue(crew, job_id)

    # Reset job to pending if it has no other assignments
    if not job.assigned_crews.exists() and job.status in ("assigned",):
        job.status = "pending"
        job.assigned_at = None
        job.save()

    notify_dispatch_change()

    return render(request, "dispatch/partials/crew_card.html", {"crew": crew})


@login_required
@require_POST
def reorder_queue_view(request, crew_id):
    crew = get_object_or_404(Crew, pk=crew_id)
    job_id = int(request.POST["job_id"])
    new_position = int(request.POST["new_position"])

    do_reorder_queue(crew, job_id, new_position)
    notify_dispatch_change()

    return render(request, "dispatch/partials/crew_card.html", {"crew": crew})


@login_required
def htmx_crew_queue(request, crew_id):
    crew = get_object_or_404(Crew, pk=crew_id)
    return render(request, "dispatch/partials/crew_queue.html", {"crew": crew})
