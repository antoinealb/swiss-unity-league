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

from championship.factories import EventOrganizerFactory, PlayerFactory
from championship.models import Event
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
        self.assertContains(resp, collection.event.name)

    def test_collection_shows_name_override(self):
        collection = CollectionFactory(name_override="Foobar")
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertContains(resp, "Foobar")

    def test_collection_shows_format(self):
        collection = CollectionFactory(format_override=Event.Format.EDH)
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertContains(resp, f"Format: {Event.Format.EDH.label}")

    def test_shows_event_format_by_default(self):
        collection = CollectionFactory()
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertContains(resp, f"Format: {collection.event.get_format_display()}")

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
        d = DecklistFactory(collection__published=True)
        resp = self.client.get(reverse("collection-details", args=[d.collection.id]))
        self.assertTrue(resp.context["show_decklist_links"])
        self.assertIn(reverse("decklist-details", args=[d.id]), resp.content.decode())

    def test_staff_link_is_shown_to_tournament_organizer(self):
        self.login()
        collection = CollectionFactory(event__organizer=self.organizer)
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertFalse(resp.context["show_decklist_links"])
        self.assertIsNotNone(resp.context["staff_link"])

    def test_hide_staff_link_for_organizer_if_published(self):
        self.login()
        collection = CollectionFactory(event__organizer=self.organizer, published=True)
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertTrue(resp.context["show_decklist_links"])
        self.assertNotContains(resp, resp.context["staff_link"])

    def test_link_submit_decklist_shown_before_deadline(self):
        collection = CollectionFactory()
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertContains(resp, "Submit decklist")
        self.assertContains(
            resp, reverse("decklist-create") + f"?collection={collection.id}"
        )

    def test_link_submit_decklist_hidden_after_deadline(self):
        collection = CollectionFactory(
            submission_deadline=timezone.now() - timezone.timedelta(hours=1)
        )
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertNotContains(resp, "Submit decklist")
        self.assertNotContains(
            resp, reverse("decklist-create") + f"?collection={collection.id}"
        )

    def test_link_submit_decklists_shown_to_organizer_past_deadline(self):
        self.login()
        collection = CollectionFactory(
            event__organizer=self.organizer,
            submission_deadline=timezone.now() - timezone.timedelta(hours=1),
        )
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertContains(resp, "Submit decklist")
        self.assertContains(
            resp, reverse("decklist-create") + f"?collection={collection.id}"
        )

    def test_links_are_shown_with_right_permissions(self):
        """Test that we can grant permissions to view unpublished decklists.

        This means that superuser, as well as judges can be granted permissions
        to view decklists for any organizer.
        """
        self.user.user_permissions.add(Permission.objects.get(codename="view_decklist"))
        self.user.save()
        self.login()
        collection = CollectionFactory(published=False)
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertFalse(resp.context["show_decklist_links"])
        self.assertIsNotNone(resp.context["staff_link"])
        self.assertContains(resp, resp.context["staff_link"])

    def test_decklists_are_not_linked_by_default(self):
        d = DecklistFactory()
        resp = self.client.get(reverse("collection-details", args=[d.collection.id]))
        self.assertNotIn(
            reverse("decklist-details", args=[d.id]), resp.content.decode()
        )
        self.assertIsNone(resp.context["staff_link"])
        self.assertFalse(resp.context["show_decklist_links"])

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

    def test_decklist_are_shown_if_using_the_staff_link(self):
        d = DecklistFactory()
        self.client.force_login(d.collection.event.organizer.user)
        resp = self.client.get(reverse("collection-details", args=[d.collection.id]))
        url = resp.context["staff_link"]
        resp = self.client.get(url)
        # We want links for judges to be sorted by mana value by default
        want_url = reverse("decklist-details", args=[d.id]) + "?sort=manavalue"
        self.assertIn(want_url, resp.content.decode())

    def test_num_players_shown(self):
        collection = CollectionFactory()
        DecklistFactory(collection=collection)
        DecklistFactory(collection=collection)
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertContains(resp, "2 Players")

    def test_organizers_can_edit_collection(self):
        collection = CollectionFactory()
        DecklistFactory(collection=collection)
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        # We don't show the edit button to non-organizers
        self.assertNotContains(resp, reverse("collection-update", args=[collection.id]))
        self.client.force_login(collection.event.organizer.user)
        # We show the edit button to organizers
        resp = self.client.get(reverse("collection-details", args=[collection.id]))
        self.assertContains(resp, reverse("collection-update", args=[collection.id]))
        self.assertContains(resp, "Edit Deadline")
