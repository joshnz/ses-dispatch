import logging
from io import BytesIO

from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from PIL import Image

from dispatch.views.sse import notify_photo_upload
from .forms import PhotoUploadForm
from .models import UploadToken

logger = logging.getLogger(__name__)

THUMBNAIL_SIZE = (200, 200)


def create_thumbnail(image_file):
    """Create a thumbnail from an uploaded image."""
    img = Image.open(image_file)
    img.thumbnail(THUMBNAIL_SIZE)
    thumb_io = BytesIO()
    img_format = "JPEG" if img.mode == "RGB" else "PNG"
    img.save(thumb_io, format=img_format)
    thumb_io.seek(0)
    return ContentFile(thumb_io.read(), name=f"thumb_{image_file.name}")


def upload_form(request, token):
    upload_token = get_object_or_404(UploadToken, token=token)
    if not upload_token.is_valid():
        return render(request, "uploads/token_expired.html")

    if request.method == "POST":
        form = PhotoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.job = upload_token.job
            photo.upload_token = upload_token
            photo.file_size = request.FILES["image"].size
            photo.content_type = request.FILES["image"].content_type
            photo.thumbnail = create_thumbnail(request.FILES["image"])
            photo.save()
            upload_token.upload_count += 1
            upload_token.save()
            notify_photo_upload(
                upload_token.job.sierra_number,
                upload_token.job.photos.count(),
            )
            return redirect("upload_success", token=token)
    else:
        form = PhotoUploadForm()

    return render(request, "uploads/upload_form.html", {
        "form": form,
        "job_address": upload_token.job.location_address,
        "remaining": upload_token.max_uploads - upload_token.upload_count,
    })


def upload_success(request, token):
    return render(request, "uploads/upload_success.html")
