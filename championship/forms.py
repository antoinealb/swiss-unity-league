from django.db.models import TextChoices, Count
from django import forms
from .models import Event
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
import datetime
import bleach


class SubmitButtonMixin:
    helper = FormHelper()
    helper.add_input(Submit("submit", "Submit", css_class="btn btn-secondary"))
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
            "decklists_url",
            "description",
        ]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
        help_texts = {
            "description": """Supports the following HTML tags: {}.
You can copy/paste the description from a website like swissmtg.ch, and the formatting will be preserved.""".format(
                ", ".join(bleach.ALLOWED_TAGS)
            ),
            "format": "If your desired format is not listed, please contact us and we'll add it.",
        }


def gets_events_available_for_upload(user):
    # TODO: Only get past events ?
    qs = Event.objects.filter(organizer__user=user)

    # Remove events that already have results
    return qs.annotate(result_cnt=Count("eventplayerresult")).filter(result_cnt=0)


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

        self.fields["event"].queryset = gets_events_available_for_upload(user)


class HtmlImporterForm(forms.Form, SubmitButtonMixin):
    standings = forms.FileField(
        help_text="The standings file saved as a web page (.html). "
        + "Go to the standings page of the last swiss round, then press Ctrl+S and save."
    )
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=True)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["event"].queryset = gets_events_available_for_upload(user)


class ImporterSelectionForm(forms.Form, SubmitButtonMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # We have to import this here in order to break a circular dependency
        from championship.importers import IMPORTER_LIST

        self.fields["site"].choices = [(p.name.upper(), p.name) for p in IMPORTER_LIST]

    site = forms.ChoiceField(
        help_text="If you use a different tool for the results and can't upload them, please send us the results via email: leoninleague@gmail.com"
        + "We will try to support as many tools as possible, but we also appreciate it if you can switch to one of the tools already supported!",
    )
