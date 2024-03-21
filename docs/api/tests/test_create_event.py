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
