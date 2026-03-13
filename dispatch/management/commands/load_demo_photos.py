"""Load demo photos from data/demo_photos/ and attach them to jobs."""
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from dispatch.models import Job
from uploads.models import Photo


DEMO_PHOTOS = [
    {
        "sierra": "S-2026-0301",
        "file": "tree_1.jpg",
        "description": "Fallen tree across driveway - view from street",
    },
    {
        "sierra": "S-2026-0301",
        "file": "tree_2.jpg",
        "description": "Fallen tree - root ball and trunk damage",
    },
]


class Command(BaseCommand):
    help = "Load demo photos and attach them to jobs"

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        source_dir = os.path.join(base_dir, "data", "demo_photos")
        media_root = settings.MEDIA_ROOT

        if not os.path.isdir(source_dir):
            self.stderr.write(f"Source directory not found: {source_dir}")
            return

        count = 0
        for entry in DEMO_PHOTOS:
            try:
                job = Job.objects.get(sierra_number=entry["sierra"])
            except Job.DoesNotExist:
                self.stderr.write(f"Job {entry['sierra']} not found, skipping")
                continue

            src = os.path.join(source_dir, entry["file"])
            if not os.path.isfile(src):
                self.stderr.write(f"File not found: {src}")
                continue

            # Use sierra number as directory name
            dest_dir = os.path.join(media_root, "job_photos", entry["sierra"])
            os.makedirs(dest_dir, exist_ok=True)
            thumbs_dir = os.path.join(dest_dir, "thumbs")
            os.makedirs(thumbs_dir, exist_ok=True)

            # Copy to media directory
            dest_file = os.path.join(dest_dir, entry["file"])
            shutil.copy2(src, dest_file)

            # Also copy as thumbnail (same image for demo)
            thumb_name = f"thumb_{entry['file']}"
            thumb_file = os.path.join(thumbs_dir, thumb_name)
            shutil.copy2(src, thumb_file)

            # Relative paths from MEDIA_ROOT
            rel_image = os.path.join("job_photos", entry["sierra"], entry["file"])
            rel_thumb = os.path.join("job_photos", entry["sierra"], "thumbs", thumb_name)

            # Create or update Photo record
            photo, created = Photo.objects.update_or_create(
                job=job,
                image=rel_image,
                defaults={
                    "thumbnail": rel_thumb,
                    "description": entry["description"],
                    "uploaded_by_name": "Demo Data",
                    "file_size": os.path.getsize(src),
                    "content_type": "image/jpeg",
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} photo: {entry['file']} -> {job.sierra_number}")
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Loaded {count} demo photos"))
