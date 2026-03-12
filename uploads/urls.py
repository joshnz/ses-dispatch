from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_form, name="public_upload"),
    path("success/", views.upload_success, name="upload_success"),
]
