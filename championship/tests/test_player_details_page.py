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

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.status import HTTP_404_NOT_FOUND

from parameterized import parameterized

from championship.factories import (
    EventFactory,
    PlayerFactory,
    RankedEventFactory,
    ResultFactory,
)
from championship.models import Event, Result
from championship.season import SEASONS_WITH_RANKING
from championship.views import (
    EVENTS,
    LAST_RESULTS,
    QP_TABLE,
    QPS,
    TABLE,
    TBODY,
    THEAD,
    TOP_FINISHES,
    Performance,
)


class PlayerDetailsTest(TestCase):
    """
    Tests for the page with a player's details
    """

    def setUp(self):
        self.client = Client()

    def get_player_details_2023(self, player):
        url = reverse("player_details_by_season", args=[player.id, "2023"])
        return self.client.get(url)

    def test_score_with_no_results(self):
        """
        Checks that the details page works even when a player has no ranking.

        This happens a lot during manual testing, but could also happen if a
        tournament gets deleted, then we have stale players with 0 points
        """
        player = PlayerFactory()
        response = self.get_player_details_2023(player)
        self.assertIn(player.name, response.content.decode())

    def test_score_in_context(self):
        """
        Checks that we have a score available in the events.
        """
        event = EventFactory(category=Event.Category.PREMIER)
        ep = ResultFactory(
            event=event,
            win_count=3,
            draw_count=1,
            loss_count=0,
        )

        response = self.get_player_details_2023(ep.player)
        gotScore = response.context_data[LAST_RESULTS][0][1].qps

        self.assertEqual(gotScore, (10 + 3) * 6)

    def test_404_when_player_is_hidden(self):
        """
        Checks that if a player wants to be hidden from leaderboard, we
        cannot access their profile page."""
        player = PlayerFactory(hidden_from_leaderboard=True)
        resp = self.get_player_details_2023(player)
        self.assertEqual(resp.status_code, HTTP_404_NOT_FOUND)

    def test_link_to_event(self):
        """
        Checks that we correctly link to events.
        """
        ep = ResultFactory()

        response = self.get_player_details_2023(ep.player)
        wantUrl = reverse("event_details", args=[ep.event.id])

        self.assertContains(response, wantUrl)

    def test_shows_link_for_admin_page(self):
        credentials = dict(username="test", password="test")
        User.objects.create_user(is_staff=True, **credentials)
        self.client.login(**credentials)

        player = PlayerFactory()
        resp = self.get_player_details_2023(player)
        resp.content.decode()
        self.assertContains(
            resp,
            reverse("admin:championship_player_change", args=[player.id]),
        )

    def test_attributes(self):
        """
        Checks that the other attributes (ranking and category) are displayed.
        """
        category = Event.Category.PREMIER
        event = EventFactory(category=category)
        ep = ResultFactory(event=event, ranking=1)

        response = self.get_player_details_2023(ep.player)
        self.assertContains(
            response,
            event.category.label,
        )
        self.assertContains(response, "1st")

    def test_qp_table(self):
        player = PlayerFactory()
        event = EventFactory(category=Event.Category.PREMIER, id=1234)
        ResultFactory(
            player=player,
            event=event,
            ranking=1,
            points=10,
            win_count=3,
            loss_count=0,
            draw_count=1,
            single_elimination_result=Result.SingleEliminationResult.QUARTER_FINALIST,
        )
        event = EventFactory(category=Event.Category.REGULAR, id=12345)
        ResultFactory(
            player=player,
            event=event,
            ranking=1,
            points=600,
            win_count=200,
            loss_count=0,
            draw_count=0,
        )
        response = self.get_player_details_2023(player)
        qps_premier = (10 + 3) * 6 + 150
        qps_regular = 600 + 3
        expected_tbody = [
            [
                QPS,
                qps_premier,
                0,
                qps_regular,
                qps_premier + qps_regular,
            ],
            [EVENTS, 1, 0, 1, 2],
        ]
        actual_tbody = response.context[QP_TABLE][TBODY]
        self.assertEqual(expected_tbody, actual_tbody)

    def test_top_finishes(self):
        player = PlayerFactory()
        ser_winner = Result.SingleEliminationResult.WINNER
        ser_quarter = Result.SingleEliminationResult.QUARTER_FINALIST
        event1 = EventFactory(category=Event.Category.PREMIER)
        event2 = EventFactory(category=Event.Category.REGIONAL)
        ResultFactory(
            points=10,
            player=player,
            event=event1,
            ranking=1,
            single_elimination_result=ser_quarter,
        )
        ResultFactory(
            points=10,
            player=player,
            event=event2,
            ranking=2,
            single_elimination_result=ser_winner,
        )
        event3 = EventFactory(category=Event.Category.REGIONAL)
        ResultFactory(points=10, player=player, event=event3, ranking=1)
        response = self.get_player_details_2023(player)
        expected_top_finishes = [
            {
                THEAD: [
                    "",
                    Event.Category.PREMIER.label,
                    Event.Category.REGIONAL.label,
                ],
                TBODY: [
                    ["1st", 0, 1],
                    ["5th-8th", 1, 0],
                ],
            },
            {
                THEAD: [
                    "",
                    Event.Category.REGIONAL.label,
                    Event.Category.REGULAR.label,
                ],
                TBODY: [["1st", 1, 0]],
            },
        ]
        actual_top_finishes = [
            finish[TABLE] for finish in response.context[TOP_FINISHES]
        ]
        self.assertEqual(expected_top_finishes, actual_top_finishes)

    def test_win_ratio_computed_correctly(self):
        p = Performance(5, 3, 1)
        self.assertEqual(p.win_ratio, 5 / 9)
        self.assertEqual(p.win_ratio_without_draws, 5 / 8)

    def test_str_format(self):
        p = Performance(5, 3, 1)
        self.assertEqual(str(p), "5 - 3 - 1")

    def test_get_performance_per_format(self):
        event = EventFactory(category=Event.Category.PREMIER)
        epr = ResultFactory(
            event=event,
            win_count=5,
            loss_count=2,
            draw_count=3,
            single_elimination_result=Result.SingleEliminationResult.FINALIST,
        )
        resp = self.get_player_details_2023(epr.player)
        perf_per_format = resp.context["performance_per_format"]
        got = perf_per_format[event.get_format_display()]

        # we are finalist, it means we won an additional 2 and lost 1
        want = Performance(5 + 2, 2 + 1, 3)
        self.assertEqual(got, want)

        got = perf_per_format["Overall"]
        self.assertEqual(got, want)

    def test_get_performance_per_format_top4(self):
        """Checks that we compute the win ratio in events with top4 only."""
        event = EventFactory(category=Event.Category.PREMIER)
        eprs = [
            ResultFactory(
                event=event,
                win_count=5,
                loss_count=2,
                draw_count=3,
                single_elimination_result=None,
            )
            for _ in range(16)
        ]
        results = [
            Result.SingleEliminationResult.WINNER,
            Result.SingleEliminationResult.FINALIST,
            Result.SingleEliminationResult.SEMI_FINALIST,
            Result.SingleEliminationResult.SEMI_FINALIST,
        ]

        for epr, result in zip(eprs, results):
            epr.single_elimination_result = result
            epr.save()

        # Winner had 2 extra wins, zero extra losses
        resp = self.get_player_details_2023(eprs[0].player)
        perf_per_format = resp.context["performance_per_format"]
        got = perf_per_format[event.get_format_display()]
        want = Performance(5 + 2, 2 + 0, 3)
        self.assertEqual(want, got)


class PlayerDetailSeasonTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    @parameterized.expand(SEASONS_WITH_RANKING)
    def test_player_details_all_seasons_work(self, season):
        player = PlayerFactory()
        event = RankedEventFactory(date=season.start_date)
        ResultFactory(event=event, player=player)
        response = self.client.get(
            reverse("player_details_by_season", args=[player.id, season.slug])
        )
        self.assertContains(response, event.name)
