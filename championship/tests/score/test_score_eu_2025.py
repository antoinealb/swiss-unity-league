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

from django.test import TestCase

from freezegun import freeze_time
from parameterized import parameterized

from championship.factories import (
    EventFactory,
    NationalLeaderboardFactory,
    PlayerFactory,
    RankedEventFactory,
    ResultFactory,
)
from championship.models import Event, Result
from championship.score import compute_scores
from championship.score.eu_season_2025 import ScoreMethodEu2025
from championship.score.types import QualificationType
from championship.seasons.definitions import EU_SEASON_2025
from multisite.tests.utils import with_site


@with_site(EU_SEASON_2025.domain)
class TestComputeScoreForEU2025(TestCase):
    def setUp(self):
        self.country_code = "IT"
        self.event = EventFactory(
            season=EU_SEASON_2025,
        )

    def compute_scores(self):
        return compute_scores(EU_SEASON_2025, self.country_code)

    def _test_compute_score(self, category, points, want_score):
        player_count = len(points)
        self.event.category = category
        self.event.save()

        players = [PlayerFactory() for _ in range(player_count)]
        for i, (player, pi) in enumerate(zip(players, points)):
            ResultFactory(
                player=player,
                event=self.event,
                points=pi,
                ranking=i + 1,
                win_count=pi // 3,
                draw_count=pi % 3,
                loss_count=0,
                player_country=self.country_code,
            )

        scores = self.compute_scores()
        for i, want in enumerate(want_score, 1):
            score = scores[i]
            self.assertEqual(want, score.total_score, f"Invalid score for player {i}")
            self.assertEqual(i, score.rank, f"Invalid rank for player {i}")

    def test_compute_score_points_weekly_3rounds(self):
        self._test_compute_score(
            category=Event.Category.REGULAR,
            points=[10, 10, 9, 5],
            want_score=[13, 13, 12, 8],
        )

    def test_compute_score_points_premier(self):
        mult = 3
        self._test_compute_score(
            category=Event.Category.PREMIER,
            points=[10, 10, 9, 5],
            want_score=[13 * mult, 13 * mult, 12 * mult, 8 * mult],
        )

    def test_compute_score_points_regional(self):
        mult = 3
        self._test_compute_score(
            category=Event.Category.REGIONAL,
            points=[10, 10, 9, 5],
            want_score=[13 * mult, 13 * mult, 12 * mult, 8 * mult],
        )

    def test_compute_score_points_qualifier(self):
        mult = 5
        self._test_compute_score(
            category=Event.Category.QUALIFIER,
            points=[10, 10, 9, 5],
            want_score=[13 * mult, 13 * mult, 12 * mult, 8 * mult],
        )

    def test_compute_score_points_grand_prix(self):
        mult = 6
        self._test_compute_score(
            category=Event.Category.GRAND_PRIX,
            points=[10, 10, 9, 5],
            want_score=[13 * mult, 13 * mult, 12 * mult, 8 * mult],
        )

    def test_ignores_players_hidden_from_leaderboard(self):
        p = PlayerFactory(hidden_from_leaderboard=True)
        ResultFactory(player=p)
        self.assertEqual(
            len(self.compute_scores()),
            0,
            "Players hidden from leaderboard should not have a score.",
        )

    def test_ignores_events_with_no_results(self):
        self.event.save()
        scores = self.compute_scores()
        for player_id, score in scores:
            self.assertEqual(
                0, score.total_score, f"Unexpected points for player {player_id}"
            )

    def test_ignore_events_outside_of_the_season_date(self):
        """Checks that events past the end of seasons don't contribute score."""
        self.event.date = EU_SEASON_2025.end_date
        self.event.date += datetime.timedelta(days=1)
        self.event.save()
        for _ in range(10):
            ResultFactory(event=self.event)
        scores = self.compute_scores()
        self.assertFalse(any(score.total_score > 0 for score in scores.values()))

    def test_ignore_events_before_the_season_date(self):
        """Checks that events past the end of seasons don't contribute score."""
        self.event.date = EU_SEASON_2025.start_date
        self.event.date -= datetime.timedelta(days=1)
        self.event.save()
        for _ in range(10):
            ResultFactory(event=self.event)
        scores = self.compute_scores()
        self.assertFalse(any(score.total_score > 0 for score in scores.values()))

    @parameterized.expand(
        [
            (Event.Category.OTHER),
            (Event.Category.NATIONAL),
        ]
    )
    def test_category_does_not_contribute_score(self, category):
        self.event.category = category
        self.event.save()
        ResultFactory(event=self.event)
        scores = self.compute_scores()
        self.assertEqual(
            0, len(scores), "Events with category 'OTHER' should not count."
        )


class ScoresWithPlayoffsTestCase(TestCase):
    def setUp(self):
        self.event = RankedEventFactory(
            season=EU_SEASON_2025,
        )
        self.player = PlayerFactory()

    def win_equivalent_for_topfinish(self, ranking, event_size):
        playoff_result = next(
            (
                r
                for r in [
                    Result.PlayoffResult.WINNER,
                    Result.PlayoffResult.FINALIST,
                    Result.PlayoffResult.SEMI_FINALIST,
                    Result.PlayoffResult.QUARTER_FINALIST,
                ]
                if ranking <= r.value
            ),
            None,
        )
        self.result = Result(
            event=self.event,
            player=self.player,
            playoff_result=playoff_result,
            ranking=ranking,
        )
        return ScoreMethodEu2025._win_equivalent_for_rank(self.result, event_size)

    @parameterized.expand(
        [
            (16, 1, 16),
            (16, 2, 10),
            (16, 3, 7),
            (16, 4, 7),
            (16, 5, 5),
            (16, 8, 5),
            (16, 9, 0),
            (16, 16, 0),
            (32, 1, 16),
            (32, 9, 0),
            (33, 1, 17),
            (33, 9, 1),
            (33, 13, 0),
            (128, 8, 7),
            (129, 8, 8),
            (256, 8, 8),
            (257, 8, 9),
            (513, 8, 10),
            (128, 1, 18),
            (129, 1, 19),
            (257, 1, 20),
            (512, 1, 20),
            (513, 1, 21),
        ]
    )
    def test_win_equivalents_for_top_finishes(
        self, event_size, ranking, want_win_equivalent
    ):
        got_win_equivalent = self.win_equivalent_for_topfinish(ranking, event_size)
        self.assertEqual(
            got_win_equivalent,
            want_win_equivalent,
            f"For event size {event_size} and ranking {ranking}, ",
        )

    def test_total_score(self):
        rounds = 7
        win_equivalent = self.win_equivalent_for_topfinish(ranking=1, event_size=128)
        qps = ScoreMethodEu2025._qps_for_result(
            result=self.result, event_size=128, has_top_8=True, total_rounds=rounds
        )
        self.assertEqual(
            qps,
            (rounds + win_equivalent) * 3 * ScoreMethodEu2025.MULT[self.event.category],
        )

    def test_swiss_round_result_more_points_than_playoffs(self):
        """
        If an event has super many rounds, it can happen that the
        Swiss round result gives more points than the playoff result.
        The maximum of the two should be taken.
        """
        result = ResultFactory(win_count=15, draw_count=1, event=self.event)
        score = ScoreMethodEu2025._qps_for_result(
            result=result, event_size=512, has_top_8=True, total_rounds=0
        )
        self.assertEqual(
            score, (15 * 3 + 1 + 3) * ScoreMethodEu2025.MULT[self.event.category]
        )

    def test_playoff_only_result(self):
        """Most MTGTop 8 results will only have a rank and a playoff result, but no points."""
        rounds = 5
        win_equivalent = 16
        result = Result(
            ranking=1, event=self.event, playoff_result=Result.PlayoffResult.WINNER
        )
        score = ScoreMethodEu2025._qps_for_result(
            result=result, event_size=17, has_top_8=True, total_rounds=rounds
        )
        self.assertEqual(
            score,
            (win_equivalent + rounds) * 3 * ScoreMethodEu2025.MULT[self.event.category],
        )

    def test_rank_only_result_ineligible_for_points(self):
        """Some MTGTop 8 results will only have a rank."""
        result = Result(ranking=17, event=self.event)
        score = ScoreMethodEu2025._qps_for_result(
            result=result, event_size=33, has_top_8=True, total_rounds=6
        )
        self.assertEqual(score, None)


@with_site(EU_SEASON_2025.domain)
class TestScoresQualified(TestCase):
    def setUp(self):
        self.country_code = "IT"
        self.num_leaderboard_qualifications = 40
        NationalLeaderboardFactory(
            country=self.country_code,
            national_invites=self.num_leaderboard_qualifications,
            continental_invites=0,
            season_slug=EU_SEASON_2025.slug,
        )

    def compute_scores(self):
        return compute_scores(EU_SEASON_2025, self.country_code)

    def test_top_leaderboard_qualified(self):
        num_players = 50
        RankedEventFactory(
            category=Event.Category.PREMIER,
            season=EU_SEASON_2025,
            players=num_players,
            with_tops=8,
            players__country=self.country_code,
        )
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = [
            QualificationType.LEADERBOARD
        ] * self.num_leaderboard_qualifications + [QualificationType.NONE] * (
            num_players - self.num_leaderboard_qualifications
        )
        self.assertEqual(want_qualified, got_qualified)

    def test_direct_qualification(self):
        num_players = 50
        RankedEventFactory(
            category=Event.Category.QUALIFIER,
            season=EU_SEASON_2025,
            players=num_players,
            with_tops=8,
            players__country=self.country_code,
        )
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = (
            [QualificationType.DIRECT]
            + [QualificationType.LEADERBOARD]
            * (self.num_leaderboard_qualifications - 1)
            + [QualificationType.NONE]
            * (num_players - self.num_leaderboard_qualifications)
        )
        self.assertEqual(want_qualified, got_qualified)

    def test_player_multiple_direct_qualifications(self):
        num_players = 50
        players = [PlayerFactory() for _ in range(num_players)]
        # Let the same player win both Qualifier events, and the invite should be passed to the next player
        RankedEventFactory(
            category=Event.Category.QUALIFIER,
            season=EU_SEASON_2025,
            players=players,
            with_tops=8,
            players__country=self.country_code,
        )
        RankedEventFactory(
            category=Event.Category.QUALIFIER,
            season=EU_SEASON_2025,
            players=players,
            with_tops=8,
        )
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = (
            [QualificationType.DIRECT] * 2
            + [QualificationType.LEADERBOARD]
            * (self.num_leaderboard_qualifications - 2)
            + [QualificationType.NONE]
            * (num_players - self.num_leaderboard_qualifications)
        )
        self.assertEqual(want_qualified, got_qualified)

    def test_trickle_down_to_second_in_second_event(self):
        """Checks that the invite trickles down to the second place on the second event."""
        num_players = 50
        winner = PlayerFactory()
        event2_players = [winner] + [PlayerFactory() for _ in range(num_players)]
        ResultFactory(
            event__category=Event.Category.QUALIFIER,
            event__date=datetime.date(2025, 1, 1),
            player=winner,
            playoff_result=Result.PlayoffResult.WINNER,
        )
        RankedEventFactory(
            category=Event.Category.QUALIFIER,
            season=EU_SEASON_2025,
            players=event2_players,
            with_tops=8,
            date=datetime.date(2025, 2, 1),
            players__country=self.country_code,
        )
        scores = self.compute_scores()

        self.assertEqual(
            scores[event2_players[1].id].qualification_type, QualificationType.DIRECT
        )

    def test_direct_qualification_outside_top_leaderboard(self):
        num_players = 60
        players = [PlayerFactory() for _ in range(num_players)]

        # Create lots of points for all players except the qualifier winner
        event = EventFactory(category=Event.Category.GRAND_PRIX, season=EU_SEASON_2025)
        [
            ResultFactory(player=player, points=1000, event=event)
            for player in players[1:]
        ]
        RankedEventFactory(
            players=players,
            category=Event.Category.QUALIFIER,
            season=EU_SEASON_2025,
            with_tops=8,
            players__country=self.country_code,
        )
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        # The last ranked player should get the direct inivte and the other invites go to the top players
        want_qualified = (
            [QualificationType.LEADERBOARD] * (self.num_leaderboard_qualifications)
            + [QualificationType.NONE]
            * (num_players - self.num_leaderboard_qualifications - 1)
            + [QualificationType.DIRECT]
        )
        self.assertEqual(want_qualified, got_qualified)

    def test_direct_invite_only_awarded_for_qualifiers_with_playoffs(self):
        """
        If the TO first enters the Swiss round results and later the playoffs,
        we want don't want the direct invite to show up yet.
        """
        num_players = 60
        RankedEventFactory(
            players=num_players,
            category=Event.Category.QUALIFIER,
            season=EU_SEASON_2025,
            players__country=self.country_code,
        )
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = [QualificationType.LEADERBOARD] * (
            self.num_leaderboard_qualifications
        ) + [QualificationType.NONE] * (
            num_players - self.num_leaderboard_qualifications
        )
        self.assertEqual(want_qualified, got_qualified)


@with_site(EU_SEASON_2025.domain)
class TestQualificationReason(TestCase):

    def setUp(self):
        self.country_code = "IT"
        self.num_leaderboard_qualifications = 40

    def compute_scores(self):
        return compute_scores(EU_SEASON_2025, self.country_code)

    def test_without_national_leadeboard_no_reasons(self):
        ResultFactory(
            ranking=1,
            event__season=EU_SEASON_2025,
            player_country=self.country_code,
        )
        score = list(self.compute_scores().values())[0]
        self.assertEqual(score.qualification_reason, "")

    def test_qualifier_reason(self):
        event = EventFactory(
            category=Event.Category.QUALIFIER,
            season=EU_SEASON_2025,
        )
        ResultFactory(
            ranking=1,
            event=event,
            playoff_result=Result.PlayoffResult.WINNER,
            player_country=self.country_code,
        )
        direct_score = list(self.compute_scores().values())[0]
        want_reason = f"Invite to European Magic Cup for 1st place at '{event.name}'"
        self.assertEqual(want_reason, direct_score.qualification_reason)

    def test_qualifier_reason_with_leaderboard(self):
        NationalLeaderboardFactory(
            country=self.country_code,
            continental_invites=1,
            season_slug=EU_SEASON_2025.slug,
        )
        event = EventFactory(
            category=Event.Category.QUALIFIER,
            season=EU_SEASON_2025,
        )
        ResultFactory(
            ranking=1,
            event=event,
            playoff_result=Result.PlayoffResult.WINNER,
            player_country=self.country_code,
        )
        direct_score = list(self.compute_scores().values())[0]
        want_reason = f"Invite to European Magic Cup for 1st place at '{event.name}'"
        self.assertEqual(want_reason, direct_score.qualification_reason)

    def test_continetal_qualification_reason(self):
        NationalLeaderboardFactory(
            country=self.country_code,
            continental_invites=1,
            season_slug=EU_SEASON_2025.slug,
        )
        ResultFactory(
            event__season=EU_SEASON_2025,
            event__category=Event.Category.REGIONAL,
            player_country=self.country_code,
        )
        direct_score = list(self.compute_scores().values())[0]
        want_reason = "Invite to European Magic Cup at the end of the season"
        self.assertEqual(want_reason, direct_score.qualification_reason)

    @freeze_time("2025-9-30")
    def test_leaderboard_qual_reason_during_season(self):
        NationalLeaderboardFactory(
            country=self.country_code,
            national_invites=1,
            continental_invites=0,
            season_slug=EU_SEASON_2025.slug,
        )
        ResultFactory(
            event__season=EU_SEASON_2025,
            event__category=Event.Category.REGIONAL,
            player_country=self.country_code,
        )
        direct_score = list(self.compute_scores().values())[0]
        want_reason = "This place qualifies for the National Championship at the end of the season"
        self.assertEqual(want_reason, direct_score.qualification_reason)

    @freeze_time("2025-10-08")
    def test_leaderboard_qual_reason_after_season(self):
        NationalLeaderboardFactory(
            country=self.country_code,
            national_invites=1,
            continental_invites=0,
            season_slug=EU_SEASON_2025.slug,
        )
        ResultFactory(
            event__season=EU_SEASON_2025,
            event__category=Event.Category.REGIONAL,
            player_country=self.country_code,
        )
        direct_score = list(self.compute_scores().values())[0]
        want_reason = "Qualified for National Championship"
        self.assertEqual(want_reason, direct_score.qualification_reason)
