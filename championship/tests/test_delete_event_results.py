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

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from championship.factories import EventFactory, EventOrganizerFactory, ResultFactory
from championship.models import Event, EventOrganizer, Result


class EventClearResult(TestCase):
    """
    Tests for the feature that create new events for tournament organizers.
    """

    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.event = EventFactory(organizer=self.organizer, date=yesterday)

        for _ in range(10):
            ResultFactory(event=self.event)

        self.login()

    def login(self):
        self.client.login(**self.credentials)

    def test_get(self):
        response = self.client.get(
            reverse(
                "event_clear_results",
                args=(self.event.id,),
            )
        )
        self.assertIn(self.event.name, response.content.decode())

    def test_clear_results(self):
        self.client.post(
            reverse(
                "event_clear_results",
                args=(self.event.id,),
            )
        )

        self.assertFalse(
            Result.objects.filter(event=self.event).exists(),
            "Results should have been cleared.",
        )

    def test_not_allowed_to_clear_result(self):
        # Change organizer for our event, we should not be able to delete
        # results anymore.
        self.event.organizer = EventOrganizerFactory()
        self.event.save()

        self.client.post(
            reverse(
                "event_clear_results",
                args=(self.event.id,),
            )
        )

        self.assertTrue(
            Result.objects.filter(event=self.event).exists(),
            "Results should not have been cleared.",
        )

    def test_tournament_too_old_for_results_deletion(self):
        self.event.date = datetime.date.today() - datetime.timedelta(days=180)
        self.event.save()

        self.client.post(
            reverse(
                "event_clear_results",
                args=(self.event.id,),
            )
        )

        self.assertTrue(
            Result.objects.filter(event=self.event).exists(),
            "We don't allow deletion of old tournament results.",
        )
