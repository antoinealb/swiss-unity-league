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

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.status import HTTP_404_NOT_FOUND

from parameterized import parameterized

from championship.factories import (
    EventFactory,
    OldCategoryRankedEventFactory,
    PlayerFactory,
    PlayerProfileFactory,
    ResultFactory,
)
from championship.models import Event, PlayerProfile, Result
from championship.score.generic import SCOREMETHOD_PER_SEASON
from championship.views import (
    EVENTS,
    LAST_RESULTS,
    QP_TABLE,
    QPS,
    TABLE,
    TBODY,
    THEAD,
    Performance,
)
from championship.views.players import CATEGORY_ORDER, sorted_most_accomplished_results
from decklists.factories import DecklistFactory
from multisite.tests.utils import site


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

    def test_score_is_replaced_by_na_for_others(self):
        """
        Checks that OTHER events are displayed but without score.
        """
        result = ResultFactory(event__category=Event.Category.OTHER, win_count=3)
        response = self.get_player_details_2023(result.player)
        got_score = response.context_data[LAST_RESULTS][0][1]
        self.assertIsNone(got_score, "Score should be None for OTHER events.")

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
            playoff_result=Result.PlayoffResult.QUARTER_FINALIST,
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
        ser_winner = Result.PlayoffResult.WINNER
        ser_quarter = Result.PlayoffResult.QUARTER_FINALIST
        event1 = EventFactory(category=Event.Category.PREMIER)
        event2 = EventFactory(category=Event.Category.REGIONAL)
        ResultFactory(
            points=10,
            player=player,
            event=event1,
            ranking=1,
            playoff_result=ser_quarter,
        )
        ResultFactory(
            points=10,
            player=player,
            event=event2,
            ranking=2,
            playoff_result=ser_winner,
        )
        response = self.get_player_details_2023(player)
        expected_top_finishes = {
            THEAD: [
                "",
                Event.Category.PREMIER.label,
                Event.Category.REGIONAL.label,
            ],
            TBODY: [
                ["1st", 0, 1],
                ["5th-8th", 1, 0],
            ],
        }

        actual_top_finishes = response.context["top_finish_table"][TABLE]
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
            playoff_result=Result.PlayoffResult.FINALIST,
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
                playoff_result=None,
            )
            for _ in range(16)
        ]
        results = [
            Result.PlayoffResult.WINNER,
            Result.PlayoffResult.FINALIST,
            Result.PlayoffResult.SEMI_FINALIST,
            Result.PlayoffResult.SEMI_FINALIST,
        ]

        for epr, result in zip(eprs, results):
            epr.playoff_result = result
            epr.save()

        # Winner had 2 extra wins, zero extra losses
        resp = self.get_player_details_2023(eprs[0].player)
        perf_per_format = resp.context["performance_per_format"]
        got = perf_per_format[event.get_format_display()]
        want = Performance(5 + 2, 2 + 0, 3)
        self.assertEqual(want, got)


class PlayerDetailsDecklistTest(TestCase):

    def get_player_details_2023(self, player):
        url = reverse("player_details_by_season", args=[player.id, "2023"])
        return self.client.get(url)

    def test_player_details_decklist(self):
        decklist = DecklistFactory(collection__published=True)
        player = decklist.player
        resp = self.get_player_details_2023(player)
        self.assertContains(resp, "Decklists")
        self.assertContains(resp, decklist.archetype)
        self.assertContains(resp, decklist.get_absolute_url())
        self.assertContains(resp, decklist.collection.get_format_display())

    def test_decklists_ordered_by_date(self):
        player = PlayerFactory()
        dates = [
            datetime.date(2023, 1, 1),
            datetime.date(2023, 1, 2),
            datetime.date(2023, 1, 3),
        ]
        decklists = [
            DecklistFactory(
                player=player, collection__event__date=date, collection__published=True
            )
            for date in dates
        ]
        resp = self.get_player_details_2023(player)
        self.assertEqual(list(resp.context["decklists"]), decklists[::-1])

    def test_hides_unpublished_decklists(self):
        player = PlayerFactory()
        DecklistFactory(player=player, collection__published=False)
        resp = self.get_player_details_2023(player)
        self.assertTrue(resp.context["decklists"].count() == 0)


class PlayerDetailSeasonTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    @parameterized.expand(SCOREMETHOD_PER_SEASON.keys())
    def test_player_details_all_seasons_work(self, season):
        with site(domain=season.domain):
            player = PlayerFactory()
            event = OldCategoryRankedEventFactory(date=season.start_date)
            ResultFactory(event=event, player=player)
            response = self.client.get(
                reverse("player_details_by_season", args=[player.id, season.slug])
            )
            self.assertContains(response, event.name)


class PlayerDetailsProfileTest(TestCase):
    """
    Tests for the player profile on the player's details page
    """

    def setUp(self):
        self.client = Client()

    def get_player_details_2023(self, player):
        url = reverse("player_details_by_season", args=[player.id, "2023"])
        return self.client.get(url)

    def test_player_profile_shown(self):
        self.profile = PlayerProfileFactory()
        ResultFactory(
            player=self.profile.player,
        )
        response = self.get_player_details_2023(self.profile.player)
        self.assertContains(response, self.profile.bio)
        self.assertContains(response, self.profile.hometown)
        self.assertContains(response, self.profile.occupation)
        self.assertContains(response, self.profile.image.url)
        self.assertContains(response, "Accomplishments")

    def test_empty_player_profile(self):
        self.profile = PlayerProfile.objects.create(
            status=PlayerProfile.Status.APPROVED,
            consent_for_website=True,
            player=PlayerFactory(),
        )
        ResultFactory(
            player=self.profile.player,
        )
        response = self.get_player_details_2023(self.profile.player)
        self.assertContains(response, "Accomplishments")

    def test_no_profile(self):
        player = PlayerFactory()
        response = self.get_player_details_2023(player)
        self.assertNotContains(response, "Accomplishments")

    def test_pending_player_profile_not_shown(self):
        self.profile = PlayerProfileFactory(status=PlayerProfile.Status.PENDING)
        ResultFactory(
            player=self.profile.player,
        )
        response = self.get_player_details_2023(self.profile.player)
        self.assertNotContains(response, "Accomplishments")

    def test_player_profile_not_shown_without_consent(self):
        self.profile = PlayerProfileFactory(consent_for_website=False)
        ResultFactory(
            player=self.profile.player,
        )
        response = self.get_player_details_2023(self.profile.player)
        self.assertNotContains(response, "Accomplishments")

    def test_pronouns(self):
        self.profile = PlayerProfileFactory(pronouns=PlayerProfile.Pronouns.SHE_HER)
        response = self.get_player_details_2023(self.profile.player)
        self.assertContains(response, self.profile.get_pronouns_display())

    def test_custom_pronouns(self):
        self.profile = PlayerProfileFactory(pronouns=PlayerProfile.Pronouns.CUSTOM)
        response = self.get_player_details_2023(self.profile.player)
        self.assertContains(response, self.profile.custom_pronouns)

    def test_age(self):
        self.profile = PlayerProfileFactory(
            date_of_birth=datetime.date.today() - datetime.timedelta(days=366 * 20)
        )
        response = self.get_player_details_2023(self.profile.player)
        self.assertContains(response, "<b>20</b>")

    def test_local_organizer_name(self):
        ResultFactory()
        result2 = ResultFactory()
        ResultFactory(event__organizer=result2.event.organizer)
        response = self.get_player_details_2023(result2.player)
        expected_name = (
            f"<p>Favorite Organizer: <b>{result2.event.organizer.name}</b></p>"
        )
        self.assertContains(response, expected_name)


class AccomplishmentsSortTesCase(TestCase):
    def setUp(self):
        self.profile = PlayerProfileFactory()

    def sort_results(self, results):
        sorted_results = sorted_most_accomplished_results([(r, None) for r in results])
        return [r[0] for r in sorted_results]

    def test_first_sort_by_playoff_result(self):
        results = [
            ResultFactory(
                player=self.profile.player,
                playoff_result=playoff_result,
            )
            for playoff_result in [
                None,
                Result.PlayoffResult.QUARTER_FINALIST,
                Result.PlayoffResult.SEMI_FINALIST,
                Result.PlayoffResult.FINALIST,
                Result.PlayoffResult.WINNER,
            ]
        ]
        sorted_results = self.sort_results(results)
        sorted_playoff_results = [r.playoff_result for r in sorted_results]
        expected_playoff_result_order = [
            Result.PlayoffResult.WINNER,
            Result.PlayoffResult.FINALIST,
            Result.PlayoffResult.SEMI_FINALIST,
            Result.PlayoffResult.QUARTER_FINALIST,
            None,
        ]
        self.assertEqual(sorted_playoff_results, expected_playoff_result_order)

    def test_second_sort_by_category(self):
        expected_category_order = CATEGORY_ORDER
        results = [
            ResultFactory(
                playoff_result=Result.PlayoffResult.WINNER,
                event__category=category,
                player=self.profile.player,
            )
            for category in reversed(expected_category_order)
        ]
        sorted_results = self.sort_results(results)
        sorted_categories = [r.event.category for r in sorted_results]
        self.assertEqual(sorted_categories, expected_category_order)

    def test_third_sort_by_ranking_if_no_playoff_result(self):
        results = [
            ResultFactory(
                event__category=Event.Category.PREMIER,
                player=self.profile.player,
                ranking=ranking,
            )
            for ranking in [4, 3, 2, 1]
        ] + [
            ResultFactory(
                event__category=Event.Category.PREMIER,
                player=self.profile.player,
                playoff_result=Result.PlayoffResult.QUARTER_FINALIST,
                ranking=8,
            )
        ]
        sorted_results = self.sort_results(results)
        sorted_ranks = [r.ranking for r in sorted_results]
        expected_rank_order = [
            8,
            1,
            2,
            3,
            4,
        ]
        self.assertEqual(sorted_ranks, expected_rank_order)

    def test_fourth_sort_by_date_if_tied(self):
        results = [
            ResultFactory(
                event__category=Event.Category.PREMIER,
                player=self.profile.player,
                event__date=date,
                playoff_result=playoff_result,
                ranking=ranking,
            )
            for ranking, playoff_result, date in [
                (2, None, datetime.date(2024, 1, 3)),
                (1, None, datetime.date(2024, 1, 1)),
                (1, None, datetime.date(2024, 1, 2)),
                (1, Result.PlayoffResult.FINALIST, datetime.date(2022, 1, 1)),
                (4, Result.PlayoffResult.FINALIST, datetime.date(2023, 1, 1)),
                (8, Result.PlayoffResult.WINNER, datetime.date(2021, 1, 1)),
            ]
        ]
        sorted_results = self.sort_results(results)
        sorted_dates = [r.event.date for r in sorted_results]
        expected_date_order = [
            datetime.date(2021, 1, 1),
            datetime.date(2023, 1, 1),
            datetime.date(2022, 1, 1),
            datetime.date(2024, 1, 2),
            datetime.date(2024, 1, 1),
            datetime.date(2024, 1, 3),
        ]
        self.assertEqual(sorted_dates, expected_date_order)
