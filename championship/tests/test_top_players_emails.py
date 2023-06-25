from django.test import TestCase, Client
from django.urls import reverse
from championship.factories import *


class TopPlayersEmailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("admin:top_players_emails")

    def test_need_to_be_authorized(self):
        response = self.client.get(self.url)
        # Check that unauthenticated users are redirected
        self.assertEqual(response.status_code, 302)

    def test_post_method(self):
        User.objects.create_user(
            username="test", password="test", is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.login(username="test", password="test")

        self.event = EventFactory()
        for i in range(3):
            player = PlayerFactory(email=f"player{i}@example.com")
            EventPlayerResultFactory(event=self.event, points=i * 3, player=player)

        response = self.client.post(self.url, {"num_of_players": 2})

        # Check that the status code is 200 (success)
        self.assertEqual(response.status_code, 200)

        # Check that the correct number of players are returned
        self.assertEqual(len(response.context["entries"]), 2)

        emails = response.context["emails"]
        # Check that the emails are correctly formatted
        self.assertEqual(emails, "player2@example.com; player1@example.com")
