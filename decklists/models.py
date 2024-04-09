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

from django.db import models
from django.urls import reverse
from django.utils import timezone

from championship.models import Event, Player


class Collection(models.Model):
    """Group of decklists that are collected at the same time and for the same purpose.

    For example, one group could be "Decklists for the Modern portion of the 2024 trial".
    """

    name = models.CharField(
        help_text="Human readable name of the Collection", max_length=128
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

    def __str__(self) -> str:
        return f"{self.name} (by {self.event.organizer.name})"

    @property
    def decklists_published(self):
        return timezone.now() > self.publication_time


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
        help_text="Content of the main deck, one entry per line (e.g. 4 Brainstorm)"
    )
    sideboard = models.TextField(
        help_text="Content of the sideboard, also one entry per line"
    )

    def __str__(self) -> str:
        return f"{self.player.name} ({self.archetype})"

    def can_be_edited(self) -> bool:
        return timezone.now() < self.collection.submission_deadline

    def get_absolute_url(self):
        return reverse("decklist-details", args=[self.id])
