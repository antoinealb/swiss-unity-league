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

from championship.factories import ResultFactory
from decklists.factories import DecklistFactory


class DecklistViewTestCase(TestCase):
    databases = ["oracle", "default"]

    def setUp(self):
        self.result = ResultFactory()
        self.player = self.result.player
        self.event = self.result.event

    def test_can_get_decklists(self):
        player = ResultFactory(event=self.event).player
        decklist1 = DecklistFactory(player=player, collection__event=self.event)
        decklist2 = DecklistFactory(player=player, collection__event=self.event)
        decklist1 = DecklistFactory(player=self.player, collection__event=self.event)
        decklist2 = DecklistFactory(player=self.player, collection__event=self.event)
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(resp, decklist1.archetype)
        self.assertContains(resp, decklist1.get_absolute_url())
        self.assertContains(resp, decklist2.archetype)
        self.assertContains(resp, decklist2.get_absolute_url())
        self.assertNotContains(resp, "Unmatched decklists")

    def test_shows_decklists_without_results(self):
        decklist = DecklistFactory(player=self.player, collection__event=self.event)
        decklist_without_result = DecklistFactory(collection__event=self.event)
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(resp, decklist.archetype)
        self.assertContains(resp, decklist.get_absolute_url())
        self.assertContains(resp, decklist_without_result.archetype)
        self.assertContains(resp, decklist_without_result.get_absolute_url())
        self.assertContains(resp, f"by {decklist_without_result.player.name}")
        self.assertContains(resp, "Unmatched decklists")
