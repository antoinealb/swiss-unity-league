import datetime

from django.test import Client, TestCase

from parameterized import parameterized

from championship.factories import *
from championship.season import SEASONS_WITH_RANKING


class RankingTestCase(TestCase):
    """
    Tests for the landing page of the website.
    """

    def setUp(self):
        self.client = Client()

    def get_by_slug(self, slug):
        url = reverse("ranking-by-season", kwargs={"slug": slug})
        return self.client.get(url)

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
        response = self.get_by_slug("2023")
        self.assertContains(response, player_with_results.name)
        self.assertNotContains(response, player_without_results.name)

    def test_ranking_for_player_hidden(self):
        """Checks that we hide hidden players from the leaderboard."""
        player = PlayerFactory(hidden_from_leaderboard=True)
        event = EventFactory(date=datetime.date(2023, 4, 1))
        EventPlayerResultFactory(player=player, points=1)
        response = self.get_by_slug("2023")
        self.assertNotContains(response, player.name)

    def test_score_properties_rendering(self):
        """Checks that the score properties are rendered correctly."""
        player = PlayerFactory()
        event = RankedEventFactory(date=datetime.date(2023, 4, 1))
        EventPlayerResultFactory(player=player, points=2, event=event)
        response = self.get_by_slug("2023")
        self.assertContains(response, """<i class="icon-star"></i>""")
        self.assertContains(response, """<i class="icon-shield"></i>""")

    def test_get_for_default_season(self):
        """Checks that we can get the page for the default season without a crash."""
        response = self.client.get("/ranking")
        self.assertEqual(200, response.status_code)

    def test_ranking_for_unknown_season_returns_404(self):
        response = self.client.get("/ranking/2022")
        self.assertEqual(404, response.status_code)

    @parameterized.expand(SEASONS_WITH_RANKING)
    def test_all_ranking(self, season_slug):
        response = self.get_by_slug(season_slug.slug)
        self.assertEqual(200, response.status_code)
