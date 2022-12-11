from django.db.models import TextChoices, Count
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
            "date",
            "format",
            "category",
            "url",
            "description",
        ]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class AetherhubImporterForm(forms.Form, SubmitButtonMixin):
    url = forms.URLField(
        label="Tournament URL",
        help_text="Link to your tournament's round page. Must be a public tournament.",
        widget=forms.URLInput(
            attrs={"placeholder": "https://aetherhub.com/Tourney/RoundTourney/123456"}
        ),
    )
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=True)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: Only get past events ?
        qs = Event.objects.filter(organizer__user=user)

        # Remove events that already have results
        qs = qs.annotate(result_cnt=Count("eventplayerresult")).filter(result_cnt=0)
        self.fields["event"].queryset = qs


class EventlinkImporterForm(forms.Form, SubmitButtonMixin):
    standings = forms.FileField(
        help_text="The standings file saved as a web page (.html)."
    )
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=True)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: Only get past events?
        qs = Event.objects.filter(organizer__user=user)

        # Remove events that already have results
        qs = qs.annotate(result_cnt=Count("eventplayerresult")).filter(result_cnt=0)
        self.fields["event"].queryset = qs


class ImporterSelectionForm(forms.Form, SubmitButtonMixin):
    class Importers(TextChoices):
        AETHERHUB = "AETHERHUB", "Aetherhub"
        EVENTLINK = "EVENTLINK", "EventLink"

    site = forms.ChoiceField(choices=Importers.choices)
