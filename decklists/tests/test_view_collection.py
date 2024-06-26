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

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.status import HTTP_200_OK

from championship.factories import EventFactory, EventOrganizerFactory, PlayerFactory
from decklists.factories import CollectionFactory, DecklistFactory
from decklists.models import Decklist


class CollectionViewTestCase(TestCase):
    def setUp(self):
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)

    def login(self):
        self.client.login(**self.credentials)

    def test_can_get_collection(self):
        collection = CollectionFactory()
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.assertIn("collection", resp.context)

    def test_decklists_are_sorted(self):
        """Checks that decklists are sorted correctly.

        We want the following sort order:
            - first by alphabetical order of player
            - then by most recent first.
        """
        pa = PlayerFactory(name="Alonso")
        pb = PlayerFactory(name="Bernardo")
        collection = CollectionFactory()
        old = timezone.now() - timezone.timedelta(hours=1)
        very_old = timezone.now() - timezone.timedelta(hours=2)

        d1 = DecklistFactory(collection=collection, player=pb, last_modified=very_old)
        d2 = DecklistFactory(collection=collection, player=pb, last_modified=old)
        d3 = DecklistFactory(collection=collection, player=pa, last_modified=very_old)
        d4 = DecklistFactory(collection=collection, player=pa, last_modified=old)

        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        want = [d4, d3, d2, d1]
        got = list(resp.context["decklists"])
        self.assertEqual(want, got)

    def test_links_are_shown_once_published(self):
        collection = CollectionFactory(publication_time=timezone.now())
        d = DecklistFactory(collection=collection)
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertTrue(resp.context["show_links"])
        self.assertIn(reverse("decklist-details", args=[d.id]), resp.content.decode())

    def test_links_are_shown_to_tournament_organizer(self):
        self.login()
        collection = CollectionFactory(event=EventFactory(organizer=self.organizer))
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertTrue(resp.context["show_links"])

    def test_links_are_shown_with_right_permissions(self):
        """Test that we can grant permissions to view unpublished decklists.

        This means that superuser, as well as judges can be granted permissions
        to view decklists for any organizer.
        """
        self.user.user_permissions.add(Permission.objects.get(codename="view_decklist"))
        self.user.save()
        self.login()
        collection = CollectionFactory()
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertTrue(resp.context["show_links"])

    def test_decklists_are_not_linked_by_default(self):
        d = DecklistFactory()
        resp = self.client.get(reverse("collection-details", args=[d.collection.id]))
        self.assertNotIn(
            reverse("decklist-details", args=[d.id]), resp.content.decode()
        )
        self.assertFalse(resp.context["show_links"])

    def test_decklist_are_shown_if_we_are_the_creator_of_the_list(self):
        collection = CollectionFactory()
        data = {
            "player_name": "Antoine Albertelli",
            "archetype": "new",
            "mainboard": "1 Fog",
            "sideboard": "1 Fly",
        }
        url = reverse("decklist-create") + f"?collection={collection.id}"
        self.client.post(url, data=data)
        decklist = Decklist.objects.all()[0]
        resp = self.client.get(
            reverse("collection-details", args=[decklist.collection.id])
        )
        self.assertIn(
            reverse("decklist-details", args=[decklist.id]), resp.content.decode()
        )

    def test_num_players_shown(self):
        collection = CollectionFactory()
        DecklistFactory(collection=collection)
        DecklistFactory(collection=collection)
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertContains(resp, "2 Players")
