import datetime
from django.test import TestCase, Client
from championship.models import Player
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
        self.assertIn(player.first_name, response.content.decode())
        self.assertIn(player.last_name, response.content.decode())
