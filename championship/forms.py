from django.db.models import TextChoices, Count
from django.core.validators import ValidationError
from django import forms
from .models import (
    Address,
    Event,
    EventPlayerResult,
    EventOrganizer,
    Player,
    PlayerAlias,
)
from championship.parsers.general_parser_functions import parse_record
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, Field
from tinymce.widgets import TinyMCE
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
            "start_time",
            "end_time",
            "format",
            "category",
            "address",
            "url",
            "decklists_url",
            "description",
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
        if organizer is not None:
            self.fields["address"].queryset = organizer.get_addresses()


class EventPlayerResultForm(forms.ModelForm):
    player_name = forms.CharField(
        widget=forms.TextInput(attrs={"list": "players-datalist"})
    )

    class Meta:
        model = EventPlayerResult
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


class AddressForm(forms.ModelForm):
    set_as_organizer_address = forms.BooleanField(required=False, initial=False)

    class Meta:
        model = Address
        fields = [
            "location_name",
            "street_address",
            "city",
            "postal_code",
            "region",
            "country",
            "set_as_organizer_address",
        ]


class OrganizerProfileEditForm(forms.ModelForm):
    class Meta:
        model = EventOrganizer
        fields = [
            "name",
            "contact",
            "default_address",
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
        help_texts = {
            "description": """Supports the following HTML tags: {}.""".format(
                ", ".join(bleach.ALLOWED_TAGS)
            ),
        }

    def __init__(self, *args, **kwargs):
        organizer = kwargs.get("instance", None)
        super().__init__(*args, **kwargs)
        self.fields["default_address"].queryset = organizer.get_addresses()


class LinkImporterForm(forms.Form, SubmitButtonMixin):
    url = forms.URLField(
        label="Tournament URL",
        help_text="Link to your tournament.",
        widget=forms.URLInput(),
        required=True,
    )
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=True)

    def __init__(self, user, *args, **kwargs):
        help_text = kwargs.pop("help_text", None)
        placeholder = kwargs.pop("placeholder", None)
        super().__init__(*args, **kwargs)
        if help_text:
            self.fields["url"].help_text = help_text
        if placeholder:
            self.fields["url"].widget.attrs["placeholder"] = placeholder

        self.fields["event"].queryset = Event.objects.available_for_result_upload(user)


class FileImporterForm(forms.Form, SubmitButtonMixin):
    standings = forms.FileField(help_text="The file that contains the standings.")
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=True)

    def __init__(self, user, *args, **kwargs):
        help_text = kwargs.pop("help_text", None)
        super().__init__(*args, **kwargs)
        if help_text:
            self.fields["standings"].help_text = help_text
        self.fields["event"].queryset = Event.objects.available_for_result_upload(user)


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


class ManualUploadMetadataForm(forms.Form, SubmitButtonMixin):
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=True)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["event"].queryset = Event.objects.available_for_result_upload(user)

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
    SingleResultForm, min_num=1, extra=32, max_num=128
)


class AddTop8ResultsForm(forms.Form, SubmitButtonMixin):
    class ResultChoiceField(forms.ModelChoiceField):
        def __init__(self, *args, **kwargs):
            queryset = EventPlayerResult.objects.none()
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
        qs = EventPlayerResult.objects.filter(event=event, ranking__lte=8).order_by(
            "ranking"
        )
        for f in self.fields.values():
            if isinstance(f, AddTop8ResultsForm.ResultChoiceField):
                f.queryset = qs

        # Make playing the whole top8 mandatory for event above 16 players.
        # Source: MTR Appendix E
        event_size = event.eventplayerresult_set.count()
        if event_size > 16:
            for key, field in self.fields.items():
                if key.startswith("quarter"):
                    field.required = True

        scnt = 0
        qcnt = 0
        for r in event.eventplayerresult_set.exclude(single_elimination_result=None):
            s = r.single_elimination_result
            if s == EventPlayerResult.SingleEliminationResult.WINNER:
                self.initial["winner"] = r
            elif s == EventPlayerResult.SingleEliminationResult.FINALIST:
                self.initial["finalist"] = r
            elif s == EventPlayerResult.SingleEliminationResult.SEMI_FINALIST:
                self.initial[f"semi{scnt}"] = r
                scnt += 1
            elif s == EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST:
                self.initial[f"quarter{qcnt}"] = r
                qcnt += 1


class ResultsDeleteForm(forms.Form, SubmitButtonMixin):
    """Event results deletion confirmation form.

    This form is empty on purpose; its only role is to have a "confirm" button
    that will be shown to the user when they want to delete results for the
    event.
    """


class TopPlayersEmailForm(forms.Form):
    num_of_players = forms.IntegerField(initial=32, min_value=1)
