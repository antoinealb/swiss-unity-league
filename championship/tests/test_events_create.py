import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from championship.models import Event, EventOrganizer


class AdminViewTestCase(TestCase):
    """
    Tests for the feature that create new events for tournament organizers.
    """

    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizer.objects.create(
            name="test TO", contact="", user=self.user
        )

    def login(self):
        self.client.login(**self.credentials)

    def test_link_not_shown_to_anonymous_users(self):
        response = self.client.get("/")

        self.assertNotIn(
            reverse("events_create"),
            response.content.decode(),
            "Anonymous users should not see the link to the event create page.",
        )

    def test_link_shown_when_authenticated(self):
        self.login()
        response = self.client.get("/")
        self.assertIn(
            reverse("events_create"),
            response.content.decode(),
            "Logged in users should get a link to creating events",
        )

    def test_create_event(self):
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "26/11/2022",
            "format": "LEGACY",
        }
        self.login()
        self.client.post(reverse("events_create"), data=data)

        event = Event.objects.all()[0]

        self.assertEqual(event.name, "Test Event")
        self.assertEqual(event.url, "https://test.example")
        self.assertEqual(event.date, datetime.date(2022, 11, 26))
        self.assertEqual(event.format, event.Format.LEGACY)