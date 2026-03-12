from django import forms
from .models import Job


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "sierra_number", "location_address", "location",
            "caller_name", "caller_phone", "description",
            "priority", "other_agencies",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "location_address": forms.Textarea(attrs={"rows": 2}),
        }


class DispatchSettingsForm(forms.Form):
    w_p = forms.FloatField(label="Priority weight", initial=0.30, min_value=0, max_value=1)
    w_t = forms.FloatField(label="Travel time weight", initial=0.40, min_value=0, max_value=1)
    w_a = forms.FloatField(label="Aging weight", initial=0.20, min_value=0, max_value=1)
    w_k = forms.FloatField(label="Capability weight", initial=0.10, min_value=0, max_value=1)
    t_max = forms.FloatField(label="Max travel time (min)", initial=60.0, min_value=1)
    max_radius_km = forms.FloatField(label="Max radius (km)", initial=80, min_value=1)
    surge_threshold = forms.IntegerField(label="Surge threshold", initial=5, min_value=1)
