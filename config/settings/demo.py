"""
Demo deployment settings.
Uses PostGIS via Docker container, local file storage for photos.
Designed for a single EC2/Lightsail instance.
"""
import os
from .base import *

DEBUG = False
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-before-deploying")
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# Database: PostGIS via Docker container
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgis://dispatch:dispatch@localhost:5432/dispatch"
)

# Parse DATABASE_URL manually to avoid requiring django-environ in demo
import re
_m = re.match(r"postgis://(\w+):(\w+)@([\w.]+):(\d+)/(\w+)", DATABASE_URL)
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": _m.group(5) if _m else "dispatch",
        "USER": _m.group(1) if _m else "dispatch",
        "PASSWORD": _m.group(2) if _m else "dispatch",
        "HOST": _m.group(3) if _m else "localhost",
        "PORT": _m.group(4) if _m else "5432",
    }
}

# Static files (served by whitenoise)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Request profiling (logs request duration + query counts)
MIDDLEWARE.append("dispatch.middleware.RequestProfilingMiddleware")

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

# Logging — profile log tracks request timing, django log tracks errors
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "django_file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
        },
        "profiler_file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "profiler.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "django_file"],
            "level": "WARNING",
        },
        "django.request": {
            "handlers": ["console", "django_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "dispatch": {
            "handlers": ["console", "django_file"],
            "level": "INFO",
        },
        "dispatch.profiler": {
            "handlers": ["profiler_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {"handlers": ["console", "django_file"], "level": "WARNING"},
}
