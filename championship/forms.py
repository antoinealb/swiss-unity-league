from django import forms
from .models import Event
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
import datetime


class SubmitButtonMixin:
    helper = FormHelper()
    helper.add_input(Submit("submit", "Submit", css_class="btn btn-primary"))
    helper.form_method = "POST"


class EventCreateForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name",
            "url",
            "date",
            "format",
            "category",
        ]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class AetherhubImporterForm(forms.Form, SubmitButtonMixin):
    url = forms.URLField(
        widget=forms.URLInput(
            attrs={"placeholder": "https://aetherhub.com/Tourney/RoundTourney/123456"}
        )
    )
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=True)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: Only get past events, and perhaps only those with no results yet ?
        self.fields["event"].queryset = Event.objects.filter(organizer__user=user)


class EventlinkImporterForm(forms.Form, SubmitButtonMixin):
    standings = forms.FileField(
        help_text="The standings file saved as a web page (.html)."
    )
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=True)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: Only get past events, and perhaps only those with no results yet ?
        self.fields["event"].queryset = Event.objects.filter(organizer__user=user)
