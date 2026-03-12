from django import forms
from .models import Photo


class PhotoUploadForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ["image", "description", "uploaded_by_name", "geo_lat", "geo_lng"]
        widgets = {
            "image": forms.FileInput(attrs={
                "accept": "image/*",
                "capture": "environment",
                "class": "form-control",
            }),
            "description": forms.Textarea(attrs={
                "rows": 2,
                "class": "form-control",
                "placeholder": "Optional: describe what the photo shows",
            }),
            "uploaded_by_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Your name (optional)",
            }),
            "geo_lat": forms.HiddenInput(),
            "geo_lng": forms.HiddenInput(),
        }
