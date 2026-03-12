from dataclasses import dataclass
from django.utils import timezone
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from dispatch.services.keywords import extract_keywords


@dataclass
class DispatchConfig:
    w_p: float = 0.30
    w_t: float = 0.40
    w_a: float = 0.20
    w_k: float = 0.10
    t_max: float = 60.0
    max_radius_km: float = 80
    surge_threshold: int = 5


def priority_score(priority: int) -> float:
    return {1: 1.0, 2: 0.5, 3: 0.2}.get(priority, 0.2)


def aging_max(priority: int) -> float:
    return {1: 15, 2: 45, 3: 120}.get(priority, 120)


def capability_match(keywords: list[str], crew_capabilities: list[str]) -> float:
    if not keywords:
        return 0.5
    matched = len(set(keywords) & set(crew_capabilities))
    return matched / len(keywords)


def _estimate_travel(origin, destination):
    """Estimate travel minutes from straight-line distance at 35 km/h."""
    if origin and destination:
        from django.contrib.gis.geos import GEOSGeometry
        if hasattr(origin, 'distance'):
            dist_deg = origin.distance(destination)
            dist_km = dist_deg * 111.32
        else:
            dist_km = 10
    else:
        dist_km = 10
    return (dist_km / 35) * 60


def recommend_dispatch(config=None):
    """
    Compute dispatch scores for all pending job / available crew pairs.
    Includes queue suggestions for busy crews with short queues.
    """
    from dispatch.models import Job, Crew, CrewJobQueue
    config = config or DispatchConfig()

    pending_jobs = Job.objects.filter(status="pending")
    available_crews = Crew.objects.filter(
        status="available"
    ).exclude(location__isnull=True)

    if pending_jobs.count() >= config.surge_threshold:
        config.w_a, config.w_k = 0.30, 0.00
        config.w_t, config.w_p = 0.40, 0.30
        config.t_max = 30.0

    results = []
    for job in pending_jobs:
        keywords = extract_keywords(job.description)
        nearby = available_crews.filter(
            location__distance_lte=(job.location, D(km=config.max_radius_km))
        ).annotate(distance=Distance("location", job.location))

        if not nearby.exists():
            nearby = available_crews.annotate(
                distance=Distance("location", job.location)
            )

        for crew in nearby:
            travel_mins = (crew.distance.km / 35) * 60
            p = priority_score(job.priority)
            t = max(0, 1 - travel_mins / config.t_max)
            wait = (timezone.now() - job.created_at).total_seconds() / 60
            a = min(1, wait / aging_max(job.priority))
            k = capability_match(keywords, crew.capabilities)
            score = config.w_p * p + config.w_t * t + config.w_a * a + config.w_k * k

            results.append({
                "job": job, "crew": crew,
                "travel_mins": round(travel_mins, 1),
                "p_score": round(p, 3), "t_score": round(t, 3),
                "a_score": round(a, 3), "k_score": round(k, 3),
                "dispatch_score": round(score, 4),
                "rec_type": "dispatch",
                "is_surge": pending_jobs.count() >= config.surge_threshold,
            })

    # Queue suggestions for busy crews with short queues
    MAX_QUEUE_DEPTH = 3
    busy_crews = Crew.objects.filter(
        status__in=["dispatched", "on_scene"]
    ).exclude(location__isnull=True)

    for crew in busy_crews:
        queue_depth = CrewJobQueue.objects.filter(crew=crew).count()
        if queue_depth >= MAX_QUEUE_DEPTH:
            continue

        if crew.current_job and crew.current_job.location:
            crew_location = crew.current_job.location
        else:
            crew_location = crew.location

        for job in pending_jobs:
            travel_mins = _estimate_travel(crew_location, job.location)
            p = priority_score(job.priority)
            t = max(0, 1 - travel_mins / config.t_max)
            wait = (timezone.now() - job.created_at).total_seconds() / 60
            a = min(1, wait / aging_max(job.priority))
            k = capability_match(
                extract_keywords(job.description), crew.capabilities
            )
            queue_penalty = 1 - (queue_depth * 0.15)
            score = (config.w_p * p + config.w_t * t + config.w_a * a + config.w_k * k)
            score *= queue_penalty

            results.append({
                "job": job, "crew": crew,
                "travel_mins": round(travel_mins, 1),
                "dispatch_score": round(score, 4),
                "rec_type": "queue",
                "queue_position": queue_depth + 1,
                "is_surge": pending_jobs.count() >= config.surge_threshold,
            })

    results.sort(key=lambda r: (r["job"].priority, -r["dispatch_score"]))
    return results


def get_crew_assignments(recommendations):
    """Greedy assignment: unique primary crew per job, alternate can repeat."""
    assigned_jobs, assigned_crews, primary = set(), set(), []
    for r in recommendations:
        if r.get("rec_type") == "queue":
            continue
        cid, jid = r["crew"].id, r["job"].id
        if cid not in assigned_crews and jid not in assigned_jobs:
            primary.append({**r, "rec_type": "primary"})
            assigned_crews.add(cid)
            assigned_jobs.add(jid)

    alternates = []
    for cid in assigned_crews:
        primary_jid = next(r["job"].id for r in primary if r["crew"].id == cid)
        for r in recommendations:
            if r.get("rec_type") == "queue":
                continue
            if r["crew"].id == cid and r["job"].id != primary_jid:
                alternates.append({**r, "rec_type": "alternate"})
                break

    queue_recs = [r for r in recommendations if r.get("rec_type") == "queue"]
    return primary + alternates + queue_recs
