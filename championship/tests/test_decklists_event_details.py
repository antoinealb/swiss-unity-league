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

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from championship.factories import ResultFactory
from decklists.factories import DecklistFactory


class DecklistViewTestCase(TestCase):

    def setUp(self):
        self.result = ResultFactory()
        self.player = self.result.player
        self.event = self.result.event
        self.decklist = DecklistFactory(
            player=self.player,
            collection__event=self.event,
            collection__publication_time=timezone.now() - timezone.timedelta(seconds=1),
        )

    def test_can_get_decklists(self):
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(resp, self.decklist.archetype)
        self.assertContains(resp, self.decklist.get_absolute_url())
        self.assertNotContains(resp, "Unmatched decklists")

    def test_shows_decklists_without_results(self):
        decklist_without_result = DecklistFactory(
            archetype="Archetype without result", collection=self.decklist.collection
        )
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(resp, self.decklist.archetype)
        self.assertContains(resp, self.decklist.get_absolute_url())
        self.assertContains(resp, decklist_without_result.archetype)
        self.assertContains(resp, decklist_without_result.get_absolute_url())
        self.assertContains(resp, f"by {decklist_without_result.player.name}")
        self.assertContains(resp, "Unmatched decklists")

    def test_doesnt_show_unpublished_decklists(self):
        self.decklist.collection.publication_time = timezone.now() + timezone.timedelta(
            hours=1
        )
        self.decklist.collection.save()
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertNotContains(resp, self.decklist.archetype)
        self.assertNotContains(resp, self.decklist.get_absolute_url())

    def test_only_shows_most_recent_decklist_of_collection(self):
        most_recent_decklist = DecklistFactory(
            archetype="Most recent decklist",
            player=self.player,
            collection=self.decklist.collection,
        )
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertNotContains(resp, self.decklist.archetype)
        self.assertNotContains(resp, self.decklist.get_absolute_url())
        self.assertContains(resp, most_recent_decklist.archetype)
        self.assertContains(resp, most_recent_decklist.get_absolute_url())
