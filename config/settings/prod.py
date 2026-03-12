from .base import *
import environ

env = environ.Env()

DEBUG = False
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Database
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

# Static files (served by whitenoise)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Photo storage
DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
AZURE_ACCOUNT_NAME = env("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = env("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_CONTAINER = env("AZURE_CONTAINER")

# Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Authentication (Entra ID)
INSTALLED_APPS += [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.microsoft",
]

SOCIALACCOUNT_PROVIDERS = {
    "microsoft": {
        "TENANT": env("AZURE_TENANT_ID"),
        "APP": {
            "client_id": env("AZURE_CLIENT_ID"),
            "secret": env("AZURE_CLIENT_SECRET"),
        },
    }
}

# SMS
TWILIO_ENABLED = env.bool("TWILIO_ENABLED", default=False)
TWILIO_SID = env("TWILIO_SID", default="")
TWILIO_TOKEN = env("TWILIO_TOKEN", default="")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", default="")

# Routing
ORS_ENABLED = env.bool("ORS_ENABLED", default=False)
ORS_API_KEY = env("ORS_API_KEY", default="")

# Logging
LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
