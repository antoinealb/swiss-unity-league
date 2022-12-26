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
        help_text="Link to your tournament. Make sure it is a public and finished tournament.",
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
        help_text="The standings file saved as a web page (.html). "
        + "Go to the standings of the last swiss round on the EventLink website, then press Ctrl+S and save."
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

    site = forms.ChoiceField(
        choices=Importers.choices,
        help_text="If you use a different tool for the results and can't upload them, please send us the results via email: leoninleague@gmail.com"
        + "We will try to support as many tools as possible, but we also appreciate it if you can switch to one of the tools already supported!",
    )
