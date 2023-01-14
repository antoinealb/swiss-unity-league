import datetime
from django.test import TestCase, Client
from championship.models import Player
from championship.factories import *


class RankingTestCase(TestCase):
    """
    Tests for the landing page of the website.
    """

    def setUp(self):
        self.client = Client()

    def test_ranking_with_no_results(self):
        """
        Checks that the ranking page works even when a player has no ranking.

        This happens a lot during manual testing, but could also happen if a
        tournament gets deleted, then we have stale players with 0 points
        """
        player = PlayerFactory()
        response = self.client.get("/ranking")
        self.assertIn(player.name, response.content.decode())

    def test_ranking_for_player_hidden(self):
        """Checks that we hide hidden players from the leaderboard."""
        player = PlayerFactory(hidden_from_leaderboard=True)
        response = self.client.get("/ranking")
        self.assertNotIn(player.name, response.content.decode())
