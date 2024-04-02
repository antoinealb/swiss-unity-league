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

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from championship.factories import (
    EventFactory,
    EventOrganizerFactory,
    EventPlayerResultFactory,
)

User = get_user_model()


class EventOrganizerDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.login(username="testuser", password="12345")

        self.organizer = EventOrganizerFactory(user=self.user)

        tomorrow = timezone.now() + timezone.timedelta(days=1)
        past_date = timezone.now() - timezone.timedelta(days=5)

        self.future_event = EventFactory(organizer=self.organizer, date=tomorrow)
        self.past_event = EventFactory(organizer=self.organizer, date=past_date)
        self.response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )

    def test_organizer_detail_view(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertTemplateUsed(self.response, "championship/organizer_details.html")
        self.assertContains(self.response, self.organizer.name)
        self.assertContains(self.response, self.future_event.name)
        self.assertContains(self.response, self.past_event.name)

    def test_organizer_detail_future_and_past(self):
        self.assertTrue("all_events" in self.response.context)
        self.assertEqual(len(self.response.context["all_events"]), 2)
        # Test Future Events
        self.assertEqual(
            self.response.context["all_events"][0]["list"][0], self.future_event
        )
        # Test Past Events
        self.assertEqual(
            self.response.context["all_events"][1]["list"][0], self.past_event
        )

    def test_past_events_contain_num_of_participants(self):
        EventPlayerResultFactory(event=self.past_event)
        self.response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        response_past_event = self.response.context["all_events"][1]
        self.assertEqual(response_past_event["has_num_players"], True)
        first_event = response_past_event["list"][0]
        self.assertEqual(first_event.num_players, 1)

    def test_organizer_detail_view_no_organizer(self):
        self.response = self.client.get(
            reverse("organizer_details", args=[9999])
        )  # assuming 9999 is an invalid ID
        self.assertEqual(self.response.status_code, 404)

    def test_organizer_reverse(self):
        edit_organizer_url = reverse("organizer_update")
        self.assertContains(self.response, f'href="{edit_organizer_url}"')

    def test_image_validation_file_type(self):
        valid_image = SimpleUploadedFile(
            "valid_image.jpg", b"file_content", content_type="image/jpeg"
        )
        invalid_image = SimpleUploadedFile(
            "invalid_image.txt", b"file_content", content_type="text/plain"
        )
        organizer = EventOrganizerFactory()
        organizer.image = invalid_image
        with self.assertRaises(ValidationError):
            organizer.full_clean()
        organizer.image = valid_image
        organizer.full_clean()

    def test_image_validation_size(self):
        valid_image = SimpleUploadedFile(
            "valid_image.jpg", b"file_content", content_type="image/jpeg"
        )
        invalid_image = SimpleUploadedFile(
            "invalid_image.jpg", b"a" * 501 * 1024, content_type="image/jpeg"
        )
        organizer = EventOrganizerFactory()
        organizer.image = invalid_image
        with self.assertRaises(ValidationError):
            organizer.full_clean()
        organizer.image = valid_image
        organizer.full_clean()


class OrganizerListViewTest(TestCase):
    def test_organizer_view(self):
        self.client = Client()
        to_with_event = EventOrganizerFactory()
        EventFactory(organizer=to_with_event)

        # create TO without events, so they shouldn't show up in list
        to_without_event = EventOrganizerFactory()

        response = self.client.get(reverse("organizer_view"))

        self.assertNotContains(response, to_without_event.name)
        self.assertContains(response, to_with_event.name)
        # Check that the city of the default address of the organizer is shown
        self.assertContains(response, to_with_event.default_address.city)
