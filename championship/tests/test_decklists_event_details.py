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

import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from championship.factories import EventFactory, ResultFactory
from championship.models import Event
from decklists.factories import CollectionFactory, DecklistFactory


class DecklistsInResultsEventDetails(TestCase):

    def setUp(self):
        self.result = ResultFactory()
        self.player = self.result.player
        self.event = self.result.event
        self.decklist = DecklistFactory(
            player=self.player,
            collection__event=self.event,
            collection__published=True,
        )

    def test_can_get_decklists(self):
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(resp, self.decklist.archetype)
        self.assertContains(resp, self.decklist.get_absolute_url())
        self.assertNotContains(resp, "Unmatched Decklists")

    def test_shows_decklists_without_matching_result(self):
        decklist_without_result = DecklistFactory(
            archetype="Archetype without result", collection=self.decklist.collection
        )
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(resp, self.decklist.archetype)
        self.assertContains(resp, self.decklist.get_absolute_url())
        self.assertContains(resp, decklist_without_result.archetype)
        self.assertContains(resp, decklist_without_result.get_absolute_url())
        self.assertContains(resp, f"by {decklist_without_result.player.name}")
        self.assertContains(resp, "Unmatched Decklists")

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


class UploadDecklistEventDetails(TestCase):

    def test_shows_link_to_submit_decklists(self):
        collection = CollectionFactory()
        event = collection.event
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(
            resp,
            reverse("collection-details", args=[event.id]),
        )
        self.assertContains(
            resp,
            f"Submit {event.get_format_display()} decklist",
        )

    def test_past_deadline_shows_view_link(self):
        collection = CollectionFactory(
            submission_deadline=datetime.date.today() - datetime.timedelta(1)
        )
        event = collection.event
        collection.save()
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(
            resp,
            reverse("collection-details", args=[event.id]),
        )
        self.assertContains(
            resp,
            f"View {event.get_format_display()} decklist",
        )


class OrganizerDecklistCollectionEventDetails(TestCase):

    def setUp(self):
        self.event = EventFactory(format=Event.Format.MODERN)
        self.client.force_login(self.event.organizer.user)

    def test_shows_create_link_if_no_collection(self):
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(
            resp, reverse("collection-create") + f"?event={self.event.id}"
        )

    def test_hides_create_link_if_collection_exists(self):
        CollectionFactory(event=self.event)
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertNotContains(
            resp, reverse("collection-create") + f"?event={self.event.id}"
        )

    def test_shows_create_link_despite_collection_for_multiformat(self):
        """For mutliformat we allow more than 1 collection."""
        self.event.format = Event.Format.MULTIFORMAT
        self.event.save()
        CollectionFactory(event=self.event)
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(
            resp, reverse("collection-create") + f"?event={self.event.id}"
        )
