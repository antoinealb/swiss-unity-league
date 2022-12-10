import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from championship.models import Event, EventOrganizer
from championship.factories import EventOrganizerFactory, EventFactory


class EventCreationTestCase(TestCase):
    """
    Tests for the feature that create new events for tournament organizers.
    """

    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)

    def login(self):
        self.client.login(**self.credentials)

    def test_link_not_shown_to_anonymous_users(self):
        response = self.client.get("/")

        self.assertNotIn(
            reverse("events_create"),
            response.content.decode(),
            "Anonymous users should not see the link to the event create page.",
        )

    def test_link_not_shown_if_no_to(self):
        """
        Checks that we don't show the link to accounts that are not TO accounts.
        """
        self.login()
        response = self.client.get("/")
        self.assertNotIn(
            reverse("events_create"),
            response.content.decode(),
            "Non TOs should not have the link",
        )

    def test_link_shown_when_authenticated(self):
        self.login()
        to = EventOrganizerFactory(user=self.user)
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
            "date": "11/26/2022",
            "format": "LEGACY",
            "category": "PREMIER",
        }
        self.login()
        to = EventOrganizerFactory(user=self.user)

        self.client.post(reverse("events_create"), data=data)

        event = Event.objects.all()[0]

        self.assertEqual(event.name, "Test Event")
        self.assertEqual(event.url, "https://test.example")
        self.assertEqual(event.date, datetime.date(2022, 11, 26))
        self.assertEqual(event.format, event.Format.LEGACY)
        self.assertEqual(event.category, event.Category.PREMIER)

    def test_create_event_redirects(self):
        """
        Checks that once the event is created, we get redirected to it.
        """
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "11/26/2022",
            "format": "LEGACY",
            "category": "PREMIER",
        }
        self.login()
        to = EventOrganizerFactory(user=self.user)

        resp = self.client.post(reverse("events_create"), data=data, follow=True)

        event = Event.objects.all()[0]

        self.assertRedirects(resp, reverse("event_details", args=[event.id]))

    def test_update_event(self):
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "11/26/2022",
            "format": "LEGACY",
            "category": "PREMIER",
        }
        self.login()
        to = EventOrganizerFactory(user=self.user)

        self.client.post(reverse("events_create"), data=data)

        data["name"] = "Updated Event"

        event = Event.objects.all()[0]

        self.client.post(reverse("event_update", args=[event.id]), data=data)

        event = Event.objects.get(pk=event.id)

        self.assertEqual(event.name, data["name"])
        self.assertEqual(event.organizer, to)

    def test_update_event_from_someone_else(self):
        other_to = EventOrganizerFactory()
        event = EventFactory(organizer=other_to)

        # Try to change an event ran by the other TO
        to = EventOrganizerFactory(user=self.user)
        self.login()
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "11/26/2022",
            "format": "LEGACY",
            "category": "PREMIER",
        }

        resp = self.client.post(reverse("event_update", args=[event.id]), data=data)

        self.assertEqual(403, resp.status_code)

    def test_update_link_shown_to_organizer(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(organizer=to)

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertNotIn(
            reverse("event_update", args=[event.id]), resp.content.decode()
        )

        self.login()

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertIn(reverse("event_update", args=[event.id]), resp.content.decode())

    def test_get_update_page(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(organizer=to)

        self.login()
        resp = self.client.get(reverse("event_update", args=[event.id]))
        self.assertEqual(200, resp.status_code)

    def test_get_delete_page(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(organizer=to)

        self.login()
        resp = self.client.get(reverse("event_delete", args=[event.id]))

    def test_delete_event(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(organizer=to)

        self.login()
        self.client.post(reverse("event_delete", args=[event.id]))

        self.assertEqual(Event.objects.count(), 0)

    def test_delete_event_for_another_to(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory()  # created for another to

        self.login()
        resp = self.client.post(reverse("event_delete", args=[event.id]))
        self.assertEqual(404, resp.status_code)
