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

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.status import HTTP_403_FORBIDDEN

from championship.factories import PlayerFactory
from championship.models import Player
from decklists.factories import CollectionFactory, DecklistFactory


class DecklistEdit(TestCase):
    def test_permission_denied_with_old_decklists(self):
        collection = CollectionFactory(
            submission_deadline=timezone.now() - timezone.timedelta(hours=1)
        )
        decklist = DecklistFactory(collection=collection)
        resp = self.client.post(reverse("decklist-update", args=[decklist.id]))
        self.assertEqual(HTTP_403_FORBIDDEN, resp.status_code)

    def test_can_change_decklist_archetype_and_sideboard(self):
        decklist = DecklistFactory()
        data = {
            "player_name": decklist.player.name,
            "archetype": "new",
            "mainboard": "1 Fog",
            "sideboard": "1 Fly",
        }
        resp = self.client.post(
            reverse("decklist-update", args=[decklist.id]), data=data
        )
        decklist.refresh_from_db()
        self.assertEqual("new", decklist.archetype)
        self.assertEqual("1 Fog", decklist.mainboard)
        self.assertEqual("1 Fly", decklist.sideboard)
        self.assertEqual(decklist.get_absolute_url(), resp.url)

    def test_can_change_decklist_player_for_another_player(self):
        decklist = DecklistFactory()
        newplayer = PlayerFactory()
        data = {
            "player_name": newplayer.name,
            "archetype": "new",
            "mainboard": "1 Fog",
            "sideboard": "1 Fly",
        }
        self.client.post(reverse("decklist-update", args=[decklist.id]), data=data)
        decklist.refresh_from_db()
        self.assertEqual(newplayer, decklist.player)

    def test_can_change_decklist_player_for_new_player(self):
        decklist = DecklistFactory()
        data = {
            "player_name": "Yoda",
            "archetype": "new",
            "mainboard": "1 Fog",
            "sideboard": "1 Fly",
        }
        self.client.post(reverse("decklist-update", args=[decklist.id]), data=data)
        decklist.refresh_from_db()
        self.assertEqual("Yoda", decklist.player.name)
        self.assertEqual(2, Player.objects.count())

    def test_autocomplete_in_edit_view(self):
        decklist = DecklistFactory()
        resp = self.client.get(reverse("decklist-update", args=[decklist.id]))
        self.assertEqual([decklist.player], list(resp.context["players"]))
