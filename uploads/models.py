import uuid

from django.db import models
from django.utils import timezone


class UploadToken(models.Model):
    job = models.ForeignKey(
        "dispatch.Job", on_delete=models.CASCADE, related_name="upload_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    max_uploads = models.SmallIntegerField(default=5)
    upload_count = models.SmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        return (self.is_active
                and self.upload_count < self.max_uploads
                and timezone.now() < self.expires_at)

    def __str__(self):
        return f"Token for {self.job.sierra_number} ({self.upload_count}/{self.max_uploads})"


class Photo(models.Model):
    job = models.ForeignKey(
        "dispatch.Job", on_delete=models.CASCADE, related_name="photos"
    )
    upload_token = models.ForeignKey(UploadToken, on_delete=models.SET_NULL, null=True)
    image = models.ImageField(upload_to="job_photos/%Y/%m/")
    thumbnail = models.ImageField(upload_to="job_photos/%Y/%m/thumbs/", blank=True)
    description = models.TextField(blank=True)
    uploaded_by_name = models.CharField(max_length=100, blank=True)
    geo_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geo_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    file_size = models.IntegerField()
    content_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.job.sierra_number} at {self.created_at}"
