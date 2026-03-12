import django.contrib.gis.db.models.fields
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sierra_number", models.CharField(max_length=20, unique=True)),
                ("location_address", models.TextField()),
                ("location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("caller_name", models.CharField(max_length=100)),
                ("caller_phone", models.CharField(max_length=20)),
                ("description", models.TextField()),
                ("priority", models.SmallIntegerField(choices=[(1, "P1 - Emergency"), (2, "P2 - Urgent"), (3, "P3 - Routine")], default=3)),
                ("other_agencies", models.JSONField(default=list)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("assigned", "Assigned"), ("en_route", "En Route"), ("on_scene", "On Scene"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assigned_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("upload_token", models.UUIDField(default=uuid.uuid4, unique=True)),
            ],
            options={
                "ordering": ["priority", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Crew",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("callsign", models.CharField(max_length=20, unique=True)),
                ("vehicle_type", models.CharField(max_length=50)),
                ("status", models.CharField(choices=[("available", "Available"), ("dispatched", "Dispatched"), ("on_scene", "On Scene"), ("returning", "Returning"), ("offline", "Offline")], default="available", max_length=20)),
                ("crew_size", models.SmallIntegerField(default=2)),
                ("capabilities", models.JSONField(default=list)),
                ("deployed_at", models.DateTimeField(blank=True, null=True)),
                ("location", django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
                ("speed_kmh", models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ("heading", models.SmallIntegerField(default=0)),
                ("position_updated_at", models.DateTimeField(auto_now=True)),
                ("current_job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_crews", to="dispatch.job")),
            ],
        ),
        migrations.CreateModel(
            name="Assignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dispatch_score", models.DecimalField(decimal_places=4, max_digits=6, null=True)),
                ("estimated_travel_mins", models.DecimalField(decimal_places=1, max_digits=6, null=True)),
                ("actual_arrival_mins", models.DecimalField(decimal_places=1, max_digits=6, null=True)),
                ("dispatched_at", models.DateTimeField(auto_now_add=True)),
                ("arrived_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("is_additional", models.BooleanField(default=False)),
                ("crew", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="dispatch.crew")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="dispatch.job")),
                ("dispatched_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="CrewJobQueue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.SmallIntegerField(default=0)),
                ("queued_at", models.DateTimeField(auto_now_add=True)),
                ("source", models.CharField(choices=[("manual", "Operator manual"), ("recommendation", "From algorithm")], default="manual", max_length=20)),
                ("crew", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="job_queue", to="dispatch.crew")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="queue_entries", to="dispatch.job")),
                ("queued_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["crew", "position"],
                "unique_together": {("crew", "position"), ("crew", "job")},
            },
        ),
    ]
