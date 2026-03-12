"""
Demo deployment settings.
Uses SQLite + SpatiaLite (no PostGIS needed), local file storage for photos.
Designed for a single EC2 instance or similar low-cost hosting.
"""
import os
from .base import *

DEBUG = False
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-before-deploying")
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# Database: SQLite + SpatiaLite (no external DB service needed)
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
SPATIALITE_LIBRARY_PATH = "mod_spatialite"

# Static files (served by whitenoise)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Photo storage: local filesystem
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# Authentication: Django built-in (no Entra ID for demo)
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# External services: all disabled for demo
TWILIO_ENABLED = False
ORS_ENABLED = False
TRACCAR_ENABLED = False

# Email: console backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Security (Caddy handles SSL termination)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    f"https://{h}" for h in ALLOWED_HOSTS if h != "*"
]

# Logging
LOGGING = {
    "version": 1,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
}
