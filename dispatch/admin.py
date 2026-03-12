from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Job, Crew, Assignment, CrewJobQueue


@admin.register(Job)
class JobAdmin(GISModelAdmin):
    list_display = ["sierra_number", "priority", "status", "location_address", "created_at"]
    list_filter = ["priority", "status"]
    search_fields = ["sierra_number", "location_address", "description"]
    readonly_fields = ["upload_token", "created_at", "updated_at"]


@admin.register(Crew)
class CrewAdmin(GISModelAdmin):
    list_display = ["callsign", "vehicle_type", "status", "crew_size", "current_job"]
    list_filter = ["status", "vehicle_type"]
    search_fields = ["callsign"]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["crew", "job", "dispatched_at", "is_additional", "dispatch_score"]
    list_filter = ["is_additional"]
    readonly_fields = ["dispatched_at"]


@admin.register(CrewJobQueue)
class CrewJobQueueAdmin(admin.ModelAdmin):
    list_display = ["crew", "job", "position", "source", "queued_at"]
    list_filter = ["source"]
    ordering = ["crew", "position"]
