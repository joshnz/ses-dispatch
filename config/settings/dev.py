from .base import *

DEBUG = True
SECRET_KEY = "dev-insecure-key-do-not-use-in-production"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# --- Database: SQLite + SpatiaLite (no PostGIS needed) ---
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
SPATIALITE_LIBRARY_PATH = "mod_spatialite"  # Adjust path for Windows if needed

# --- File storage: local filesystem (no Azure Blob) ---
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# --- Authentication: Django built-in (no Entra ID) ---
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# --- SMS: disabled (upload links shown in console) ---
TWILIO_ENABLED = False

# --- Routing: stub (no OpenRouteService API key needed) ---
ORS_ENABLED = False

# --- GPS: disabled (no Traccar) ---
TRACCAR_ENABLED = False

# --- Email: console backend (for password reset etc.) ---
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- Static files ---
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
