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

"""Test showing that the example API code does not get stale."""

import datetime
import os.path
import shlex
import subprocess

from django.contrib.auth.models import User
from django.test import LiveServerTestCase

from championship.factories import EventFactory, EventOrganizerFactory
from championship.models import Event, EventPlayerResult
from docs.api.create_event import create_example_event, get_api_token


class CreateEventApiExample(LiveServerTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="test")
        self.organizer = EventOrganizerFactory(user=self.user)

    def test_can_create_event(self):
        file = os.path.dirname(os.path.abspath(__file__))
        file = os.path.join(file, "..", "create_event.py")
        instance = self.live_server_url
        cmd = f"{file} --instance {instance} --username test --password test"
        subprocess.check_output(shlex.split(cmd))

        self.assertTrue(Event.objects.exists(), "Event should have been created")

    def test_can_upload_results(self):
        file = os.path.dirname(os.path.abspath(__file__))
        file = os.path.join(file, "..", "upload_event_results.py")

        # Create an event for upload
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        EventFactory(
            date=yesterday, category=Event.Category.REGIONAL, organizer=self.organizer
        )

        instance = self.live_server_url
        cmd = f"{file} --instance {instance} --username test --password test"
        subprocess.check_output(shlex.split(cmd))

        self.assertEqual(7, EventPlayerResult.objects.count())
        self.assertEqual(
            EventPlayerResult.SingleEliminationResult.WINNER,
            EventPlayerResult.objects.get(
                player__name="Darth Vader"
            ).single_elimination_result,
        )
