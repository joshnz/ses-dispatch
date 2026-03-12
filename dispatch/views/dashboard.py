from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from dispatch.models import Job, Crew, Assignment
from dispatch.services.algorithm import recommend_dispatch, get_crew_assignments
from dispatch.forms import DispatchSettingsForm


@login_required
def dashboard(request):
    jobs = Job.objects.exclude(status__in=["completed", "cancelled"])
    crews = Crew.objects.all()
    recommendations = get_crew_assignments(recommend_dispatch())

    context = {
        "jobs": jobs,
        "crews": crews,
        "recommendations": recommendations,
        "pending_count": jobs.filter(status="pending").count(),
        "active_count": jobs.exclude(status="pending").count(),
        "available_crews": crews.filter(status="available").count(),
        "dispatched_crews": crews.exclude(status__in=["available", "offline"]).count(),
    }
    return render(request, "dispatch/dashboard.html", context)


@login_required
def job_queue(request):
    jobs = Job.objects.all()
    return render(request, "dispatch/job_queue.html", {"jobs": jobs})


@login_required
def crew_status(request):
    crews = Crew.objects.all()
    return render(request, "dispatch/crew_status.html", {"crews": crews})


@login_required
def recommendations(request):
    recs = get_crew_assignments(recommend_dispatch())
    return render(request, "dispatch/recommendations.html", {"recommendations": recs})


@login_required
def dispatch_settings(request):
    if request.method == "POST":
        form = DispatchSettingsForm(request.POST)
        if form.is_valid():
            request.session["dispatch_config"] = form.cleaned_data
    else:
        config = request.session.get("dispatch_config", {})
        form = DispatchSettingsForm(initial=config)

    return render(request, "dispatch/settings.html", {"form": form})


@login_required
def htmx_metrics(request):
    jobs = Job.objects.exclude(status__in=["completed", "cancelled"])
    crews = Crew.objects.all()
    context = {
        "pending_count": jobs.filter(status="pending").count(),
        "active_count": jobs.exclude(status="pending").count(),
        "available_crews": crews.filter(status="available").count(),
        "dispatched_crews": crews.exclude(status__in=["available", "offline"]).count(),
    }
    return render(request, "dispatch/partials/metrics.html", context)


@login_required
def htmx_map_data(request):
    jobs = Job.objects.exclude(status__in=["completed", "cancelled"])
    crews = Crew.objects.exclude(location__isnull=True)

    job_data = [
        {
            "id": j.id,
            "sierra": j.sierra_number,
            "lat": j.location.y,
            "lng": j.location.x,
            "priority": j.priority,
            "status": j.status,
            "address": j.location_address,
            "assigned_crews": [
                {"callsign": c.callsign, "lat": c.location.y, "lng": c.location.x}
                for c in j.assigned_crews.exclude(location__isnull=True)
            ],
        }
        for j in jobs
    ]

    crew_data = [
        {
            "id": c.id,
            "callsign": c.callsign,
            "lat": c.location.y,
            "lng": c.location.x,
            "status": c.status,
        }
        for c in crews
    ]

    return JsonResponse({"jobs": job_data, "crews": crew_data})


@login_required
def htmx_job_detail_modal(request, pk):
    job = get_object_or_404(Job, pk=pk)
    assignments = Assignment.objects.filter(job=job).order_by("-dispatched_at")
    photos = job.photos.all() if hasattr(job, "photos") else []
    return render(request, "dispatch/partials/job_detail_modal.html", {
        "job": job,
        "assignments": assignments,
        "photos": photos,
    })
