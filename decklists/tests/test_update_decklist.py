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

from championship.factories import PlayerFactory
from championship.models import Player
from decklists.factories import CollectionFactory, DecklistFactory
from decklists.models import Decklist


class DecklistEdit(TestCase):
    def setUp(self):
        self.data = {
            "player_name": "player",
            "archetype": "new",
            "content": "1 Fog\nSideboard\n1 Fly",
        }

    def test_permission_denied_past_deadline(self):
        decklist = DecklistFactory(
            collection__submission_deadline=timezone.now() - timezone.timedelta(hours=1)
        )
        resp = self.client.post(
            reverse("decklist-update", args=[decklist.id]), data=self.data
        )
        self.assertRedirects(resp, reverse("decklist-details", args=[decklist.id]))
        decklist.refresh_from_db()
        self.assertNotEqual(decklist.archetype, self.data["archetype"])

    def test_organizer_can_edit_decklist_past_deadline(self):
        decklist = DecklistFactory(
            collection__submission_deadline=timezone.now() - timezone.timedelta(hours=1)
        )
        self.client.force_login(decklist.collection.event.organizer.user)
        self.client.post(reverse("decklist-update", args=[decklist.id]), data=self.data)
        decklist.refresh_from_db()
        self.assertEqual(decklist.archetype, self.data["archetype"])

    def test_can_update_decklist_past_deadline_with_staff_key(self):
        decklist = DecklistFactory(
            collection__submission_deadline=timezone.now() - timezone.timedelta(hours=1)
        )
        resp = self.client.post(
            reverse("decklist-update", args=[decklist.id])
            + f"?staff_key={decklist.collection.staff_key}",
            data=self.data,
        )
        decklist.refresh_from_db()
        self.assertEqual(decklist.archetype, self.data["archetype"])

        # Check that the staff_key is in the redirected URL
        expected_redirect_url = reverse("decklist-details", args=[decklist.id])
        self.assertEqual(
            resp.url,
            f"{expected_redirect_url}?staff_key={decklist.collection.staff_key}",
        )

    def test_can_change_decklist_archetype_and_sideboard(self):
        decklist = DecklistFactory()
        data = {
            "player_name": decklist.player.name,
            "archetype": "new",
            "content": "1 Fog\nSideboard\n1 Fry",
        }
        resp = self.client.post(
            reverse("decklist-update", args=[decklist.id]), data=data
        )
        decklist.refresh_from_db()
        self.assertEqual("new", decklist.archetype)
        self.assertEqual(decklist.get_absolute_url(), resp.url)

    def test_can_change_decklist_player_for_another_player(self):
        decklist = DecklistFactory()
        newplayer = PlayerFactory()
        self.data["player_name"] = newplayer.name
        self.client.post(reverse("decklist-update", args=[decklist.id]), data=self.data)
        decklist.refresh_from_db()
        self.assertEqual(newplayer, decklist.player)

    def test_can_change_decklist_player_for_new_player(self):
        decklist = DecklistFactory()
        self.data["player_name"] = "Yoda"
        self.client.post(reverse("decklist-update", args=[decklist.id]), data=self.data)
        decklist.refresh_from_db()
        self.assertEqual("Yoda", decklist.player.name)
        self.assertEqual(2, Player.objects.count())

    def test_autocomplete_in_edit_view(self):
        decklist = DecklistFactory()
        resp = self.client.get(reverse("decklist-update", args=[decklist.id]))
        self.assertEqual([decklist.player], list(resp.context["players"]))


class DecklistCreate(TestCase):
    data = {
        "player_name": "Antoine Albertelli",
        "archetype": "new",
        "content": "1 Fog\nSideboard\n1 Fry\n",
    }

    def setUp(self):
        self.collection = CollectionFactory()
        self.url = reverse("decklist-create") + f"?collection={self.collection.id}"

    def test_create(self):
        self.client.post(self.url, data=self.data)
        d = Decklist.objects.get(player__name="Antoine Albertelli")
        self.assertEqual(d.archetype, "new")
        self.assertEqual(d.collection, self.collection)

    def test_create_past_deadline(self):
        self.collection.submission_deadline = timezone.now()
        self.collection.save()
        resp = self.client.post(self.url, data=self.data)
        self.assertRedirects(
            resp, reverse("collection-details", args=[self.collection.id])
        )
        self.assertFalse(Decklist.objects.exists())

    def test_create_organizer_past_deadline(self):
        self.collection.submission_deadline = timezone.now()
        self.collection.save()
        self.client.force_login(self.collection.event.organizer.user)
        self.client.post(self.url, data=self.data)
        self.assertTrue(Decklist.objects.exists())

    def test_create_decklist_saves_in_session(self):
        """Checks that we save a decklist as ours in a session."""
        self.client.post(self.url, data=self.data)
        self.client.post(self.url, data=self.data)
        decklists = Decklist.objects.filter(player__name="Antoine Albertelli").order_by(
            "last_modified"
        )
        self.assertEqual(
            self.client.session["owned_decklists"], [d.id.hex for d in decklists]
        )


class DecklistDeletion(TestCase):

    def test_can_delete_decklist_before_deadline(self):
        decklist = DecklistFactory(collection__published=False)
        self.client.post(reverse("decklist-delete", args=[decklist.id]))
        self.assertFalse(Decklist.objects.exists())

    def test_cannot_delete_decklist_after_deadline(self):
        decklist = DecklistFactory(collection__published=True)
        self.client.post(reverse("decklist-delete", args=[decklist.id]))
        self.assertTrue(Decklist.objects.exists())

    def test_organizer_can_delete_decklist_after_deadline(self):
        decklist = DecklistFactory(collection__published=True)
        self.client.force_login(decklist.collection.event.organizer.user)
        self.client.post(reverse("decklist-delete", args=[decklist.id]))
        self.assertFalse(Decklist.objects.exists())

    def test_can_delete_decklist_with_staff_key_after_deadline(self):
        decklist = DecklistFactory(collection__published=True)
        self.client.post(
            reverse("decklist-delete", args=[decklist.id])
            + f"?staff_key={decklist.collection.staff_key}"
        )
        self.assertFalse(Decklist.objects.exists())
