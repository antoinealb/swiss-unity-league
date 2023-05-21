import datetime
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

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.event = EventFactory(organizer=self.organizer, date=yesterday)

        for _ in range(10):
            EventPlayerResultFactory(event=self.event)

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
            EventPlayerResult.objects.filter(event=self.event).exists(),
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
            EventPlayerResult.objects.filter(event=self.event).exists(),
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
            EventPlayerResult.objects.filter(event=self.event).exists(),
            "We don't allow deletion of old tournament results.",
        )
