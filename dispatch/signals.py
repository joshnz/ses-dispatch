import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Job

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Job)
def on_job_created(sender, instance, created, **kwargs):
    if not created:
        return

    from .services.algorithm import recommend_dispatch
    from .models import CrewJobQueue
    from .views.sse import notify_dispatch_change

    recommendations = recommend_dispatch()

    queue_recs = [r for r in recommendations if r.get("rec_type") == "queue"]
    for rec in queue_recs:
        crew = rec["crew"]
        job = rec["job"]

        existing_queue = CrewJobQueue.objects.filter(
            crew=crew, position__gt=0
        ).select_related("job").order_by("position")

        for entry in existing_queue:
            if job.priority < entry.job.priority:
                logger.info(
                    "Queue suggestion: P%d %s should precede P%d %s for %s",
                    job.priority, job.sierra_number,
                    entry.job.priority, entry.job.sierra_number,
                    crew.callsign,
                )
                break

    notify_dispatch_change()
