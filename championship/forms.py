# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

import bleach
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Submit
from tinymce.widgets import TinyMCE

from championship.parsers.general_parser_functions import parse_record

from .models import (
    Address,
    Event,
    EventOrganizer,
    Player,
    PlayerAlias,
    PlayerProfile,
    RecurrenceRule,
    RecurringEvent,
    Result,
)


class SubmitButtonMixin:
    helper = FormHelper()
    helper.add_input(Submit("submit", "Submit", css_class="btn btn-secondary"))
    helper.form_method = "POST"


class AllRequiredMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True


class UserForm(AllRequiredMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["first_name", "last_name", "email", "password1", "password2"]


class EventCreateForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "name",
            "date",
            "start_time",
            "end_time",
            "format",
            "category",
            "address",
            "url",
            "decklists_url",
            "description",
            "image",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "description": TinyMCE(
                mce_attrs={
                    "toolbar": "undo redo | bold italic | link unlink | bullist numlist",
                    "link_assume_external_targets": "http",
                },
            ),
        }
        help_texts = {
            "description": """Supports the following HTML tags: {}.
You can copy/paste the description from a website like swissmtg.ch, and the formatting will be preserved.""".format(
                ", ".join(bleach.ALLOWED_TAGS)
            ),
            "format": "If your desired format is not listed, please contact us and we'll add it.",
        }

    def __init__(self, *args, **kwargs):
        organizer = kwargs.pop("organizer", None)
        super(EventCreateForm, self).__init__(*args, **kwargs)
        if not organizer:
            organizer = self.instance.organizer
        self.fields["address"].queryset = organizer.get_addresses()


class UpdateAllEventForm(EventCreateForm):
    """Used for the RecurringEvents to update several event at once."""

    class Meta(EventCreateForm.Meta):
        exclude = ["date", "category"]


class ResultForm(forms.ModelForm):
    player_name = forms.CharField(
        widget=forms.TextInput(attrs={"list": "players-datalist"})
    )

    class Meta:
        model = Result
        fields = [
            "player_name",
            "win_count",
            "loss_count",
            "draw_count",
            "deck_name",
            "decklist_url",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["player_name"].initial = (
            self.instance.player.name if self.instance and self.instance.player else ""
        )

    def clean_player_name(self):
        player_name = self.cleaned_data.get("player_name")
        if not player_name:
            raise forms.ValidationError("Player name cannot be empty.")
        return player_name

    def save(self, commit=True):
        instance = super().save(commit=False)

        new_name = self.cleaned_data["player_name"]
        old_name = instance.player.name

        if new_name != old_name:
            try:
                player = PlayerAlias.objects.get(name=new_name).true_player
            except PlayerAlias.DoesNotExist:
                player, _ = Player.objects.get_or_create(name=new_name)
            instance.player = player

        instance.points = (
            self.cleaned_data["win_count"] * 3 + self.cleaned_data["draw_count"]
        )

        if commit:
            instance.save()
        return instance


class RegistrationAddressForm(forms.ModelForm):

    class Meta:
        model = Address
        fields = [
            "location_name",
            "street_address",
            "postal_code",
            "city",
            "region",
            "country",
        ]


class AddressForm(RegistrationAddressForm):
    set_as_main_address = forms.BooleanField(required=False, initial=False)


class EventOrganizerForm(forms.ModelForm):
    class Meta:
        model = EventOrganizer
        fields = [
            "name",
            "contact",
            "url",
            "default_address",
            "image",
            "description",
        ]
        widgets = {
            "description": TinyMCE(
                mce_attrs={
                    "toolbar": "undo redo | bold italic | link unlink | bullist numlist",
                    "link_assume_external_targets": "http",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        organizer = kwargs.get("instance", None)
        super().__init__(*args, **kwargs)
        if organizer:
            self.fields["default_address"].queryset = organizer.get_addresses()
        else:
            # Remvove the default address field if we're creating a new organizer
            self.fields.pop("default_address")


class SelectEventForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event"] = forms.ModelChoiceField(
            queryset=Event.objects.available_for_result_upload(user),
            required=True,
            help_text="Please create an event first before uploading results. Ensure to upload the results within 30 days from the event date.",
        )


class LinkImporterForm(SelectEventForm, SubmitButtonMixin):
    url = forms.URLField(
        label="Tournament URL",
        help_text="Link to your tournament.",
        widget=forms.URLInput(),
        required=True,
    )

    def __init__(self, user, *args, **kwargs):
        help_text = kwargs.pop("help_text", None)
        placeholder = kwargs.pop("placeholder", None)
        super().__init__(user, *args, **kwargs)
        if help_text:
            self.fields["url"].help_text = help_text
        if placeholder:
            self.fields["url"].widget.attrs["placeholder"] = placeholder


class FileImporterForm(SelectEventForm, SubmitButtonMixin):
    standings = forms.FileField(help_text="The file that contains the standings.")

    def __init__(self, user, *args, **kwargs):
        help_text = kwargs.pop("help_text", None)
        super().__init__(user, *args, **kwargs)
        if help_text:
            self.fields["standings"].help_text = help_text


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


def validate_result_format(value: str):
    try:
        parse_record(value)
    except ValueError:
        raise ValidationError("Score should be in the win-loss-draw format.")


class SingleResultForm(forms.Form):
    name = forms.CharField(
        label="Name",
        widget=forms.TextInput(
            attrs={"placeholder": "First Last", "list": "players-datalist"}
        ),
    )
    points = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "e.g. 3-0-1"}),
        validators=[validate_result_format],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = SingleResultFormHelper(self)


class ManualUploadMetadataForm(SelectEventForm, SubmitButtonMixin):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False


class SingleResultFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = "post"
        self.layout = Div(
            Field("name", wrapper_class="col"),
            Field("points", wrapper_class="col"),
            css_class="row",
        )
        self.form_show_labels = False
        self.render_required_fields = True
        self.form_tag = False


ResultsFormset = forms.formset_factory(
    SingleResultForm, min_num=1, extra=15, max_num=128
)


class AddTop8ResultsForm(forms.Form, SubmitButtonMixin):
    class ResultChoiceField(forms.ModelChoiceField):
        def __init__(self, *args, **kwargs):
            queryset = Result.objects.none()
            super().__init__(queryset=queryset, *args, **kwargs)

        def label_from_instance(self, obj):
            return obj.player.name

    winner = ResultChoiceField(label="Winner")
    finalist = ResultChoiceField(label="Finalist")
    semi0 = ResultChoiceField(label="Semifinalist")
    semi1 = ResultChoiceField(label="Semifinalist")
    quarter0 = ResultChoiceField(label="Quarterfinalist", required=False)
    quarter1 = ResultChoiceField(label="Quarterfinalist", required=False)
    quarter2 = ResultChoiceField(label="Quarterfinalist", required=False)
    quarter3 = ResultChoiceField(label="Quarterfinalist", required=False)

    def __init__(self, event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Result.objects.filter(event=event, ranking__lte=8).order_by("ranking")
        for f in self.fields.values():
            if isinstance(f, AddTop8ResultsForm.ResultChoiceField):
                f.queryset = qs

        # Make playing the whole top8 mandatory for event above 16 players.
        # Source: MTR Appendix E
        event_size = event.result_set.count()
        if event_size > 16:
            for key, field in self.fields.items():
                if key.startswith("quarter"):
                    field.required = True

        scnt = 0
        qcnt = 0
        for r in event.result_set.exclude(single_elimination_result=None):
            s = r.single_elimination_result
            if s == Result.SingleEliminationResult.WINNER:
                self.initial["winner"] = r
            elif s == Result.SingleEliminationResult.FINALIST:
                self.initial["finalist"] = r
            elif s == Result.SingleEliminationResult.SEMI_FINALIST:
                self.initial[f"semi{scnt}"] = r
                scnt += 1
            elif s == Result.SingleEliminationResult.QUARTER_FINALIST:
                self.initial[f"quarter{qcnt}"] = r
                qcnt += 1


class ResultsDeleteForm(forms.Form, SubmitButtonMixin):
    """Event results deletion confirmation form.

    This form is empty on purpose; its only role is to have a "confirm" button
    that will be shown to the user when they want to delete results for the
    event.
    """


class RecurrenceRuleForm(forms.ModelForm):
    class Meta:
        model = RecurrenceRule
        fields = ["type", "weekday", "week"]
        help_texts = {
            "type": None,
            "weekday": None,
            "week": None,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False


RecurrenceRuleModelFormSet = forms.modelformset_factory(
    RecurrenceRule, form=RecurrenceRuleForm, min_num=1, extra=0, max_num=10
)


class RecurringEventForm(forms.ModelForm):
    class Meta:
        model = RecurringEvent
        fields = ["name", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class PlayerProfileForm(forms.ModelForm, SubmitButtonMixin):
    player_name = forms.CharField(
        label="Player name",
        max_length=100,
        required=True,
    )

    class Meta:
        model = PlayerProfile
        fields = [
            "player_name",
            "pronouns",
            "custom_pronouns",
            "date_of_birth",
            "hometown",
            "occupation",
            "bio",
            "image",
            "team_name",
            "consent_for_website",
            "consent_for_stream",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.player = self.cleaned_data["player"]
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("player_name")
        try:
            player = PlayerAlias.objects.get(name=name).true_player
        except PlayerAlias.DoesNotExist:
            try:
                player = Player.objects.get(name=name)
            except Player.DoesNotExist:
                raise ValidationError(f"Player '{name}' does not exist.")
        cleaned_data["player"] = player
        return cleaned_data
