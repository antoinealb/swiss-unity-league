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

from championship.models import Event, Player
from decklists.models import Collection, Decklist


class DecklistForm(forms.ModelForm):
    class Meta:
        model = Decklist
        fields = ["player_name", "archetype", "mainboard", "sideboard"]

    player_name = forms.CharField(
        label="Player",
        widget=forms.TextInput(
            attrs={"placeholder": "First Last", "list": "players-datalist"}
        ),
    )

    def __init__(self, *args, **kwargs):
        try:
            self.collection = kwargs.pop("collection")
        except KeyError:
            self.collection = None

        super().__init__(*args, **kwargs)
        if self.instance:
            try:
                self.fields["player_name"].initial = self.instance.player.name
            except Decklist.player.RelatedObjectDoesNotExist:
                pass

        self.fields["archetype"].widget.attrs["placeholder"] = "E.g. 'Burn'"
        self.fields["mainboard"].widget.attrs["placeholder"] = "e.g. 4 Brainstorm"
        self.fields["sideboard"].widget.attrs[
            "placeholder"
        ] = "e.g. 4 Surgical Extraction"

    def save(self, commit=True):
        instance = super().save(commit=False)

        name = self.cleaned_data["player_name"]

        instance.player, created = Player.objects.get_or_create_by_name(name)

        if self.collection:
            instance.collection = self.collection

        if commit:
            instance.save()
        return instance


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["submission_deadline", "publication_time", "format_override"]

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)
        if not self.event:
            self.event = self.instance.event

        if self.event.format != Event.Format.MULTIFORMAT:
            self.fields.pop("format_override")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.event = self.event

        if commit:
            instance.save()
        return instance
