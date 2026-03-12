from django.db import models, transaction
from django.db.models import F

from dispatch.models import CrewJobQueue


def queue_job_for_crew(crew, job, position=None, user=None, source="manual"):
    """Add a job to a crew's queue at the given position (or end)."""
    with transaction.atomic():
        existing = CrewJobQueue.objects.filter(crew=crew)

        if position is None:
            max_pos = existing.aggregate(models.Max("position"))["position__max"]
            position = (max_pos or 0) + 1
            if max_pos is None:
                position = 0
        else:
            existing.filter(position__gte=position).update(
                position=F("position") + 1
            )

        entry = CrewJobQueue.objects.create(
            crew=crew, job=job, position=position,
            queued_by=user, source=source,
        )

        _sync_active_job(crew)
        return entry


def promote_next_job(crew):
    """Called when active job completes. Promotes position 1 to 0."""
    with transaction.atomic():
        CrewJobQueue.objects.filter(crew=crew, position=0).delete()

        CrewJobQueue.objects.filter(crew=crew).update(
            position=F("position") - 1
        )

        _sync_active_job(crew)

        next_entry = CrewJobQueue.objects.filter(crew=crew, position=0).first()
        return next_entry


def reorder_queue(crew, job_id, new_position):
    """Move a queued job to a new position (operator drag-and-drop)."""
    with transaction.atomic():
        entry = CrewJobQueue.objects.get(crew=crew, job_id=job_id)
        old_position = entry.position

        if old_position == 0 or new_position == 0:
            return

        if new_position > old_position:
            CrewJobQueue.objects.filter(
                crew=crew,
                position__gt=old_position,
                position__lte=new_position,
            ).update(position=F("position") - 1)
        else:
            CrewJobQueue.objects.filter(
                crew=crew,
                position__gte=new_position,
                position__lt=old_position,
            ).update(position=F("position") + 1)

        entry.position = new_position
        entry.save()


def remove_from_queue(crew, job_id):
    """Remove a job from a crew's queue (operator cancels queued job)."""
    with transaction.atomic():
        entry = CrewJobQueue.objects.filter(crew=crew, job_id=job_id).first()
        if not entry:
            return
        pos = entry.position
        entry.delete()

        CrewJobQueue.objects.filter(
            crew=crew, position__gt=pos
        ).update(position=F("position") - 1)

        _sync_active_job(crew)


def _sync_active_job(crew):
    """Keep Crew.current_job in sync with position 0 queue entry."""
    active = CrewJobQueue.objects.filter(crew=crew, position=0).first()
    crew.current_job = active.job if active else None
    crew.save(update_fields=["current_job"])
