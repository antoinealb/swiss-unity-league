from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from championship.factories import (
    EventOrganizerFactory,
    EventFactory,
    EventPlayerResultFactory,
)
from django.contrib.auth import get_user_model

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
        self.assertEquals(response_past_event["has_num_players"], True)
        first_event = response_past_event["list"][0]
        self.assertEquals(first_event.num_players, 1)

    def test_organizer_detail_view_no_organizer(self):
        self.response = self.client.get(
            reverse("organizer_details", args=[9999])
        )  # assuming 9999 is an invalid ID
        self.assertEqual(self.response.status_code, 404)

    def test_organizer_reverse(self):
        edit_organizer_url = reverse("organizer_update")
        self.assertContains(self.response, f'href="{edit_organizer_url}"')
