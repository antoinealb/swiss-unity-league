from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from championship.models import Event, EventOrganizer, EventPlayerResult
from championship.factories import (
    EventOrganizerFactory,
    EventFactory,
    EventPlayerResultFactory,
)


class EventClearResult(TestCase):
    """
    Tests for the feature that create new events for tournament organizers.
    """

    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)

    def login(self):
        self.client.login(**self.credentials)

    def test_get(self):
        self.login()
        event = EventFactory(organizer=self.organizer)
        response = self.client.get(
            reverse(
                "event_clear_results",
                args=(event.id,),
            )
        )
        self.assertIn(event.name, response.content.decode())

    def test_clear_results(self):
        self.login()
        event = EventFactory(organizer=self.organizer)
        for _ in range(10):
            EventPlayerResultFactory(event=event)

        self.client.post(
            reverse(
                "event_clear_results",
                args=(event.id,),
            )
        )

        self.assertFalse(EventPlayerResult.objects.filter(event=event).exists())

    def test_not_allowed_to_clear_result(self):
        self.login()
        event = EventFactory()  # for another TO
        for _ in range(10):
            EventPlayerResultFactory(event=event)

        self.client.post(
            reverse(
                "event_clear_results",
                args=(event.id,),
            )
        )

        self.assertTrue(EventPlayerResult.objects.filter(event=event).exists())
