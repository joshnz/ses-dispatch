import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("dispatch", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UploadToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("max_uploads", models.SmallIntegerField(default=5)),
                ("upload_count", models.SmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="upload_tokens", to="dispatch.job")),
            ],
        ),
        migrations.CreateModel(
            name="Photo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="job_photos/%Y/%m/")),
                ("thumbnail", models.ImageField(blank=True, upload_to="job_photos/%Y/%m/thumbs/")),
                ("description", models.TextField(blank=True)),
                ("uploaded_by_name", models.CharField(blank=True, max_length=100)),
                ("geo_lat", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("geo_lng", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("file_size", models.IntegerField()),
                ("content_type", models.CharField(max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="dispatch.job")),
                ("upload_token", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="uploads.uploadtoken")),
            ],
        ),
    ]
