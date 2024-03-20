"""Test showing that the example API code does not get stale."""

import os.path
import shlex
import subprocess

from django.contrib.auth.models import User
from django.test import LiveServerTestCase

from championship.factories import EventOrganizerFactory
from championship.models import Event
from docs.api.create_event import create_example_event, get_api_token


class CreateEventApiExample(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="test", password="test")
        cls.organizer = EventOrganizerFactory(user=cls.user)

    def test_can_create_event(self):
        file = os.path.dirname(os.path.abspath(__file__))
        file = os.path.join(file, "..", "create_event.py")
        instance = self.live_server_url
        cmd = f"{file} --instance {instance} --username test --password test"
        subprocess.check_output(shlex.split(cmd))

        self.assertTrue(Event.objects.exists(), "Event should have been created")
