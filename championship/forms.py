from django import forms
from .models import Event
import datetime


class EventCreateForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name",
            "url",
            "date",
            "format",
        ]
