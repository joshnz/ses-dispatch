import uuid

from django.conf import settings
from django.contrib.gis.db import models
from django.utils import timezone


class Job(models.Model):
    class Priority(models.IntegerChoices):
        EMERGENCY = 1, "P1 - Emergency"
        URGENT = 2, "P2 - Urgent"
        ROUTINE = 3, "P3 - Routine"

    class Status(models.TextChoices):
        PENDING = "pending"
        ASSIGNED = "assigned"
        EN_ROUTE = "en_route"
        ON_SCENE = "on_scene"
        COMPLETED = "completed"
        CANCELLED = "cancelled"

    sierra_number = models.CharField(max_length=20, unique=True)
    location_address = models.TextField()
    location = models.PointField(srid=4326)
    caller_name = models.CharField(max_length=100)
    caller_phone = models.CharField(max_length=20)
    description = models.TextField()
    priority = models.SmallIntegerField(choices=Priority.choices, default=3)
    other_agencies = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=Status.choices, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    upload_token = models.UUIDField(default=uuid.uuid4, unique=True)

    class Meta:
        ordering = ["priority", "-created_at"]

    def __str__(self):
        return f"{self.sierra_number} - {self.get_priority_display()}"

    @property
    def status_color(self):
        return {
            "pending": "warning",
            "assigned": "info",
            "en_route": "primary",
            "on_scene": "success",
            "completed": "secondary",
            "cancelled": "dark",
        }.get(self.status, "secondary")

    @property
    def age_minutes(self):
        delta = timezone.now() - self.created_at
        return int(delta.total_seconds() / 60)

    @property
    def age_display(self):
        mins = self.age_minutes
        if mins < 60:
            return f"{mins} minutes"
        hours = mins // 60
        remainder = mins % 60
        return f"{hours} hours and {remainder} minutes"


class Crew(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available"
        DISPATCHED = "dispatched"
        ON_SCENE = "on_scene"
        RETURNING = "returning"
        OFFLINE = "offline"

    callsign = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=Status.choices, default="available")
    crew_size = models.SmallIntegerField(default=2)
    capabilities = models.JSONField(default=list)
    current_job = models.ForeignKey(
        Job, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assigned_crews"
    )
    deployed_at = models.DateTimeField(null=True, blank=True)
    location = models.PointField(srid=4326, null=True, blank=True)
    speed_kmh = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    heading = models.SmallIntegerField(default=0)
    position_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.callsign

    @property
    def status_color(self):
        return {
            "available": "success",
            "dispatched": "primary",
            "on_scene": "warning",
            "returning": "info",
            "offline": "secondary",
        }.get(self.status, "secondary")


class Assignment(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="assignments")
    crew = models.ForeignKey(Crew, on_delete=models.CASCADE, related_name="assignments")
    dispatch_score = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    estimated_travel_mins = models.DecimalField(max_digits=6, decimal_places=1, null=True)
    actual_arrival_mins = models.DecimalField(max_digits=6, decimal_places=1, null=True)
    dispatched_at = models.DateTimeField(auto_now_add=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_additional = models.BooleanField(default=False)
    dispatched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.crew} -> {self.job} at {self.dispatched_at}"


class CrewJobQueue(models.Model):
    crew = models.ForeignKey(
        Crew, on_delete=models.CASCADE, related_name="job_queue"
    )
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="queue_entries"
    )
    position = models.SmallIntegerField(default=0)
    queued_at = models.DateTimeField(auto_now_add=True)
    queued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    source = models.CharField(
        max_length=20,
        choices=[
            ("manual", "Operator manual"),
            ("recommendation", "From algorithm"),
        ],
        default="manual",
    )

    class Meta:
        ordering = ["crew", "position"]
        unique_together = [("crew", "position"), ("crew", "job")]

    def __str__(self):
        return f"{self.crew.callsign} pos {self.position}: {self.job.sierra_number}"
