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
        tournament gets deleted, then we have stale players with no results.
        In this case the player shouldn't show up in the ranking.
        """
        player_with_results = PlayerFactory()
        EventPlayerResultFactory(player=player_with_results, points=1)
        player_without_results = PlayerFactory()
        response = self.client.get("/ranking")
        self.assertContains(response, player_with_results.name)
        self.assertNotContains(response, player_without_results.name)

    def test_ranking_for_player_hidden(self):
        """Checks that we hide hidden players from the leaderboard."""
        player = PlayerFactory(hidden_from_leaderboard=True)
        EventPlayerResultFactory(player=player, points=1)
        response = self.client.get("/ranking")
        self.assertNotContains(response, player.name)
