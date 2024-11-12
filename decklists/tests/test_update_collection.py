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

from championship.factories import EventFactory, EventOrganizerFactory
from championship.models import Event
from decklists.factories import CollectionFactory


class CollectionCreateTestCase(TestCase):
    def setUp(self):
        self.event = EventFactory(format=Event.Format.MULTIFORMAT)
        self.client.force_login(self.event.organizer.user)
        self.data = {
            "submission_deadline": timezone.now() + datetime.timedelta(days=1),
            "publication_time": timezone.now() + datetime.timedelta(days=2),
            "format_override": Event.Format.LEGACY,
        }
        self.url = reverse("collection-create") + f"?event={self.event.id}"

    def test_contains_name_of_event(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.name)

    def test_form_initial_submission_deadline_9am(self):
        response = self.client.get(self.url)
        initial_submission_deadline = (
            response.context["form"].fields["submission_deadline"].initial
        )
        self.assertEqual(initial_submission_deadline.date(), self.event.date)
        self.assertEqual(initial_submission_deadline.hour, 9)

    def test_form_initial_submission_deadline_start_time_of_event(self):
        self.event.start_time = datetime.time(10)
        self.event.save()
        response = self.client.get(self.url)
        initial_submission_deadline = (
            response.context["form"].fields["submission_deadline"].initial
        )
        self.assertEqual(initial_submission_deadline.date(), self.event.date)
        self.assertEqual(initial_submission_deadline.hour, 10)

    def test_form_initial_pulication_time_next_day(self):
        response = self.client.get(self.url)
        initial_publication_time = (
            response.context["form"].fields["publication_time"].initial
        )
        self.assertEqual(
            initial_publication_time, self.event.date + datetime.timedelta(days=1)
        )

    def test_can_create_collection(self):
        self.client.post(self.url, self.data)
        collection = self.event.collection_set.first()
        self.assertEqual(
            collection.submission_deadline, self.data["submission_deadline"]
        )
        self.assertEqual(collection.publication_time, self.data["publication_time"])
        self.assertEqual(collection.format_override, self.data["format_override"])

    def test_create_collections_for_other_organizers_forbidden(self):
        self.event.organizer = EventOrganizerFactory()
        self.event.save()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.event.collection_set.count(), 0)

    def test_publication_time_before_submission_deadline_shows_error(self):
        self.data["publication_time"] = timezone.now() - datetime.timedelta(days=1)
        response = self.client.post(self.url, self.data)
        self.assertIn(
            "Submission deadline must be before decklist publication.",
            response.context["form"].errors["__all__"],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.event.collection_set.count(), 0)

    def test_format_override_not_submitted_for_single_format_events(self):
        self.event.format = Event.Format.MODERN
        self.event.save()
        response = self.client.get(self.url)
        self.assertNotIn("format_override", response.context["form"].fields)
        response = self.client.post(self.url, self.data)
        collection = self.event.collection_set.first()
        self.assertEqual(collection.format_override, None)


class CollectionUpdateTestCase(TestCase):
    def setUp(self):
        self.collection = CollectionFactory(event__format=Event.Format.MULTIFORMAT)
        self.client.force_login(self.collection.event.organizer.user)
        self.data = {
            "submission_deadline": timezone.now() + datetime.timedelta(days=1),
            "publication_time": timezone.now() + datetime.timedelta(days=2),
            "format_override": Event.Format.LEGACY,
        }
        self.url = reverse("collection-update", args=[self.collection.id])

    def test_contains_name_of_event(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.collection.event.name)

    def test_form_no_initial_datetimes(self):
        """Unlike when creating a collection, during an update we don't want to initialize the datetime fields."""
        response = self.client.get(self.url)
        initial_submission_deadline = (
            response.context["form"].fields["submission_deadline"].initial
        )
        self.assertIsNone(initial_submission_deadline)
        initial_publication_time = (
            response.context["form"].fields["publication_time"].initial
        )
        self.assertIsNone(initial_publication_time)

    def test_can_update_collection(self):
        self.client.post(self.url, self.data)
        collection = self.collection.event.collection_set.first()
        self.assertEqual(
            collection.submission_deadline, self.data["submission_deadline"]
        )
        self.assertEqual(collection.publication_time, self.data["publication_time"])
        self.assertEqual(collection.format_override, self.data["format_override"])

    def test_update_collections_for_other_organizers_forbidden(self):
        self.collection.event.organizer = EventOrganizerFactory()
        self.collection.event.save()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 403)
        self.collection.refresh_from_db()
        # Make sure the collection was not updated
        self.assertNotEqual(
            self.collection.submission_deadline, self.data["submission_deadline"]
        )

    def test_update_publication_time_before_submission_deadline_shows_error(self):
        self.data["publication_time"] = timezone.now() - datetime.timedelta(days=1)
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Submission deadline must be before decklist publication.",
            response.context["form"].errors["__all__"],
        )
        self.collection.refresh_from_db()
        # Make sure the collection was not updated
        self.assertNotEqual(
            self.collection.publication_time, self.data["publication_time"]
        )

    def test_format_override_not_submitted_for_single_format_events(self):
        self.collection.event.format = Event.Format.MODERN
        self.collection.event.save()
        response = self.client.get(self.url)
        self.assertNotIn("format_override", response.context["form"].fields)
        response = self.client.post(self.url, self.data)
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.format_override, None)
