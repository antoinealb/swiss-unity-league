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

import uuid

from django.core.validators import ValidationError
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from parsita import Failure

from championship.models import Event, Player
from decklists.parser import DecklistParser


class CollectionQuerySet(models.QuerySet):
    def published(self):
        return self.filter(publication_time__lte=timezone.now())

    def unpublished(self):
        return self.exclude(publication_time__lte=timezone.now())


class Collection(models.Model):
    """Group of decklists that are collected at the same time and for the same purpose.

    For example, one group could be "Decklists for the Modern portion of the 2024 trial".
    """

    objects = CollectionQuerySet.as_manager()

    name_override = models.CharField(
        help_text="Name of the Decklist Collection. If left empty, we will show the name of the event.",
        max_length=128,
        blank=True,
    )
    submission_deadline = models.DateTimeField(
        help_text="Time until new decklists can be created for this group or existing ones can be edited."
    )
    publication_time = models.DateTimeField(
        help_text="Time at which the decklists will be revealed."
    )
    event = models.ForeignKey(
        Event,
        help_text="Event for which those decklists are.",
        on_delete=models.CASCADE,
    )
    format_override = models.CharField(
        verbose_name="Format",
        choices=Event.Format.choices,
        max_length=10,
        null=True,
        blank=True,
        help_text="Format of the decklist. If left empty, we will use the format of the event.",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(submission_deadline__lte=F("publication_time")),
                name="decklists_collection_submission_before_publication",
                violation_error_message="Submission deadline must be before decklist publication.",
            )
        ]

    objects = CollectionQuerySet.as_manager()

    def __str__(self) -> str:
        return f"{self.name} (by {self.event.organizer.name})"

    @property
    def name(self):
        return self.name_override or self.event.name

    @property
    def format(self):
        return self.format_override or self.event.format

    def get_format_display(self):
        return Event.Format(self.format).label

    @property
    def is_past_deadline(self):
        return timezone.now() > self.submission_deadline

    @property
    def decklists_published(self):
        return timezone.now() > self.publication_time

    def get_absolute_url(self):
        return reverse("collection-details", args=[self.id])


class DecklistQuerySet(models.QuerySet):
    def published(self):
        return self.filter(collection__publication_time__lte=timezone.now())

    def unpublished(self):
        return self.exclude(collection__publication_time__lte=timezone.now())


def validate_decklist_format(value: str):
    parsed = DecklistParser.deck.parse(value)
    if isinstance(parsed, Failure):
        raise ValidationError(f"Invalid decklist: {parsed}")


class Decklist(models.Model):
    """A single deck, for a single player, in a single Colection."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    collection = models.ForeignKey(Collection, on_delete=models.RESTRICT)
    player = models.ForeignKey(
        Player, help_text="Who is playing this deck.", on_delete=models.RESTRICT
    )
    archetype = models.CharField(
        help_text="Player-submitted name for the deck (e.g. 'Burn')", max_length=64
    )
    last_modified = models.DateTimeField(
        help_text="Last modification timestamp.", auto_now=True
    )
    mainboard = models.TextField(
        help_text="Content of the main deck, one entry per line (e.g. 4 Brainstorm)",
        validators=[validate_decklist_format],
    )
    sideboard = models.TextField(
        help_text=(
            "Content of the sideboard, also one entry per line."
            " If you use extra decks, such as attractions, add them here as well."
        ),
        validators=[validate_decklist_format],
    )

    objects = DecklistQuerySet.as_manager()

    def __str__(self) -> str:
        return f"{self.player.name} ({self.archetype})"

    def can_be_edited(self) -> bool:
        return not self.collection.is_past_deadline

    def get_absolute_url(self):
        return reverse("decklist-details", args=[self.id])
