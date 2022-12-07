import datetime
from django.test import TestCase, Client
from championship.models import Player, Event
from championship.factories import *
from django.urls import reverse


class PlayerDetailsTest(TestCase):
    """
    Tests for the page with a player's details
    """

    def setUp(self):
        self.client = Client()

    def test_score_with_no_results(self):
        """
        Checks that the details page works even when a player has no ranking.

        This happens a lot during manual testing, but could also happen if a
        tournament gets deleted, then we have stale players with 0 points
        """
        player = PlayerFactory()
        response = self.client.get(reverse("player_details", args=[player.id]))
        self.assertIn(player.name, response.content.decode())

    def test_score_in_context(self):
        """
        Checks that we have a score available in the events.
        """
        player = PlayerFactory()
        event = EventFactory(category=Event.Category.PREMIER)
        ep = EventPlayerResult.objects.create(points=10, player=player, event=event)

        response = self.client.get(reverse("player_details", args=[player.id]))
        gotScore = response.context_data["last_events"][0].qps

        self.assertEqual(gotScore, (10 + 3) * 6)

    def test_link_to_event(self):
        """
        Checks that we correctly link to events.
        """
        player = PlayerFactory()
        event = EventFactory(category=Event.Category.PREMIER, id=1234)
        ep = EventPlayerResult.objects.create(points=10, player=player, event=event)

        response = self.client.get(reverse("player_details", args=[player.id]))
        wantUrl = reverse("event_details", args=[event.id])

        self.assertIn(wantUrl, response.content.decode())
