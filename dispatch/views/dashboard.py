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
    jobs = Job.objects.exclude(status__in=["completed", "cancelled"])
    priority_filter = request.GET.get("priority", "")
    status_filter = request.GET.get("status", "")
    if priority_filter:
        jobs = jobs.filter(priority=int(priority_filter))
    if status_filter:
        jobs = jobs.filter(status=status_filter)

    # Get recommendations for each pending job
    recs = recommend_dispatch()
    job_recs = {}
    for r in recs:
        if r.get("rec_type") == "queue":
            continue
        jid = r["job"].id
        if jid not in job_recs or r["dispatch_score"] > job_recs[jid]["dispatch_score"]:
            job_recs[jid] = r

    # Annotate jobs with their top recommendation
    job_list = []
    for job in jobs:
        rec = job_recs.get(job.id)
        job.rec_crew = rec["crew"].callsign if rec else None
        job.rec_eta = rec["travel_mins"] if rec else None
        job.rec_score = rec["dispatch_score"] if rec else None
        job_list.append(job)

    available_crews = Crew.objects.filter(status="available")

    return render(request, "dispatch/job_queue.html", {
        "jobs": job_list,
        "available_crews": available_crews,
        "priority_filter": priority_filter,
        "status_filter": status_filter,
    })


@login_required
def crew_status(request):
    crews = Crew.objects.all()
    return render(request, "dispatch/crew_status.html", {"crews": crews})


@login_required
def recommendations(request):
    from django.utils import timezone as tz
    from collections import OrderedDict

    recs = get_crew_assignments(recommend_dispatch())
    is_surge = any(r.get("is_surge") for r in recs)
    pending_count = Job.objects.filter(status="pending").count()

    # Group recommendations by crew, preserving crew order
    crews = Crew.objects.exclude(status="offline")
    crew_data = OrderedDict()
    for crew in crews:
        time_away = None
        if crew.deployed_at:
            delta = tz.now() - crew.deployed_at
            total_mins = int(delta.total_seconds() / 60)
            if total_mins >= 60:
                time_away = f"{total_mins // 60}h {total_mins % 60:02d}m"
            else:
                time_away = f"{total_mins}m"
            away_mins = total_mins
        else:
            away_mins = 0

        crew_recs = [r for r in recs if r["crew"].id == crew.id]
        crew_data[crew.id] = {
            "crew": crew,
            "time_away": time_away,
            "away_mins": away_mins,
            "primary": [r for r in crew_recs if r.get("rec_type") == "primary"],
            "alternate": [r for r in crew_recs if r.get("rec_type") == "alternate"],
            "queue": [r for r in crew_recs if r.get("rec_type") == "queue"],
        }

    return render(request, "dispatch/recommendations.html", {
        "crew_data": crew_data,
        "is_surge": is_surge,
        "pending_count": pending_count,
    })


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
def htmx_job_queue_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    photos = job.photos.all() if hasattr(job, "photos") else []
    available_crews = Crew.objects.filter(status="available")

    # Find best recommendation for this job
    rec = None
    if job.status == "pending":
        recs = recommend_dispatch()
        for r in recs:
            if r["job"].id == job.id and r.get("rec_type") != "queue":
                if rec is None or r["dispatch_score"] > rec["dispatch_score"]:
                    rec = r

    return render(request, "dispatch/partials/job_queue_detail.html", {
        "job": job,
        "photos": photos,
        "available_crews": available_crews,
        "rec": rec,
    })


@login_required
def htmx_crew_detail(request, pk):
    from django.utils import timezone
    crew = get_object_or_404(Crew, pk=pk)
    time_away = None
    if crew.deployed_at:
        delta = timezone.now() - crew.deployed_at
        total_mins = int(delta.total_seconds() / 60)
        if total_mins >= 60:
            time_away = f"{total_mins // 60}h {total_mins % 60:02d}m"
        else:
            time_away = f"{total_mins}m"
    photos = []
    if crew.current_job and hasattr(crew.current_job, "photos"):
        photos = crew.current_job.photos.all()

    return render(request, "dispatch/partials/crew_detail_panel.html", {
        "crew": crew,
        "time_away": time_away,
        "photos": photos,
    })


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
