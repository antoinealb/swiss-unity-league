# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

from django.contrib.sites.models import Site
from django.shortcuts import reverse
from django.test import TestCase

from parameterized import parameterized

from championship.factories import (
    OldCategoryRankedEventFactory,
    PlayerFactory,
    ResultFactory,
)
from championship.models import Event
from championship.score.generic import SCOREMETHOD_PER_SEASON
from championship.seasons.definitions import EU_SEASON_2025, SEASON_2025
from multisite.constants import GLOBAL_DOMAIN, SWISS_DOMAIN
from multisite.tests.utils import site


class RankingTestCase(TestCase):
    """
    Tests for the leaderboard page.
    """

    def get_by_slug(self, slug):
        url = reverse("ranking_by_season", kwargs={"slug": slug})
        return self.client.get(url)

    def test_ranking_with_no_results(self):
        """
        Checks that the ranking page works even when a player has no ranking.

        This happens a lot during manual testing, but could also happen if a
        tournament gets deleted, then we have stale players with no results.
        In this case the player shouldn't show up in the ranking.
        """
        result = ResultFactory(event__category=Event.Category.REGULAR)
        PlayerFactory()  # another player, without results
        players = self.get_by_slug("2023").context["players"]
        self.assertEqual([p.name for p in players], [result.player.name])

    def test_ranking_for_player_hidden(self):
        """Checks that we hide hidden players from the leaderboard."""
        ResultFactory(player__hidden_from_leaderboard=True, points=1)
        players = self.get_by_slug("2023").context["players"]
        self.assertEqual(players, [])

    def test_score_properties_rendering(self):
        """Checks that the score properties are rendered correctly."""
        event = OldCategoryRankedEventFactory(date=datetime.date(2023, 4, 1))
        ResultFactory(event=event)
        response = self.get_by_slug("2023")
        player = response.context["players"][0]
        self.assertEqual(player.score.byes, 2)
        self.assertEqual(player.score.qualification_type.name, "LEADERBOARD")

    def test_get_for_default_season(self):
        """Checks that we can get the page for the default season without a crash."""
        response = self.client.get("/ranking")
        self.assertEqual(200, response.status_code)

    def test_ranking_for_unknown_season_returns_404(self):
        response = self.client.get("/ranking/2022/")
        self.assertEqual(404, response.status_code)

    @parameterized.expand(SCOREMETHOD_PER_SEASON.keys())
    def test_all_ranking(self, season):
        with site(domain=season.domain):
            response = self.get_by_slug(season.slug)
            self.assertEqual(200, response.status_code)


@site(EU_SEASON_2025.domain)
class NationalRankingPageTestCase(TestCase):
    def setUp(self):
        self.season = EU_SEASON_2025

    def get_ranking(self, country_code):
        return self.client.get(
            reverse(
                "ranking_by_season_country",
                kwargs={"slug": self.season.slug, "country_code": country_code},
            )
        )

    def test_ranking_per_country(self):
        result = ResultFactory(
            event__season=self.season,
            player_country="FR",
        )
        resp = self.get_ranking("FR")
        self.assertContains(resp, result.player.name)

    def test_hides_players_from_other_country(self):
        result = ResultFactory(event__season=self.season, player_country="IT")
        resp = self.get_ranking("FR")
        self.assertNotContains(resp, result.player.name)

    def test_wrong_country_shows_empty_ranking(self):
        resp = self.get_ranking("FOO")
        self.assertEqual(200, resp.status_code)

    @site(SWISS_DOMAIN)
    def test_swiss_ranking_ignores_results_from_other_sites(self):
        result = ResultFactory(
            event__season=SEASON_2025,
            event__category=Event.Category.REGULAR,
            event__organizer__site=Site.objects.get(domain=GLOBAL_DOMAIN),
        )
        resp = self.client.get(
            reverse("ranking_by_season", kwargs={"slug": SEASON_2025.slug})
        )
        self.assertEqual(200, resp.status_code)
        self.assertNotContains(resp, result.player.name)
