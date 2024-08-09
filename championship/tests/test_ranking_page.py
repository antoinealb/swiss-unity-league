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

from django.shortcuts import reverse
from django.test import Client, TestCase

from parameterized import parameterized

from championship.factories import (
    EventFactory,
    PlayerFactory,
    RankedEventFactory,
    ResultFactory,
)
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
        ResultFactory(player=player_with_results, points=1)
        player_without_results = PlayerFactory()
        response = self.get_by_slug("2023")
        self.assertContains(response, player_with_results.name)
        self.assertNotContains(response, player_without_results.name)

    def test_ranking_for_player_hidden(self):
        """Checks that we hide hidden players from the leaderboard."""
        player = PlayerFactory(hidden_from_leaderboard=True)
        EventFactory(date=datetime.date(2023, 4, 1))
        ResultFactory(player=player, points=1)
        response = self.get_by_slug("2023")
        self.assertNotContains(response, player.name)

    def test_score_properties_rendering(self):
        """Checks that the score properties are rendered correctly."""
        player = PlayerFactory()
        event = RankedEventFactory(date=datetime.date(2023, 4, 1))
        ResultFactory(player=player, points=2, event=event)
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
