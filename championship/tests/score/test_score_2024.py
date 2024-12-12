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

from freezegun import freeze_time

from championship.factories import (
    Event2024Factory,
    PlayerFactory,
    ResultFactory,
    SpecialRewardFactory,
)
from championship.models import Event, Result
from championship.score import compute_scores
from championship.score.season_2024 import ScoreMethod2024
from championship.score.types import QualificationType
from championship.seasons.definitions import SEASON_2024


class TestComputeScoreFor2024(TestCase):
    def setUp(self):
        self.event = Event2024Factory()

    def compute_scores(self):
        return compute_scores(SEASON_2024)

    def _test_compute_score(self, category, points, want_score):
        player_count = len(points)
        self.event.category = category
        self.event.save()

        players = [PlayerFactory() for _ in range(player_count)]
        for i, (player, pi) in enumerate(zip(players, points)):
            Result.objects.create(
                player=player,
                event=self.event,
                points=pi,
                ranking=i + 1,
                win_count=pi // 3,
                draw_count=pi % 3,
                loss_count=0,
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
        self._test_compute_score(
            category=Event.Category.PREMIER,
            points=[10, 10, 9, 5],
            want_score=[78, 78, 72, 48],
        )

    def test_compute_score_points_regional(self):
        self._test_compute_score(
            category=Event.Category.REGIONAL,
            points=[10, 10, 9, 5],
            want_score=[52, 52, 48, 32],
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
        self.event.date = SEASON_2024.end_date
        self.event.date += datetime.timedelta(days=1)
        self.event.save()
        for _ in range(10):
            ResultFactory(event=self.event)
        scores = self.compute_scores()
        self.assertFalse(any(score.total_score > 0 for score in scores.values()))

    def test_ignore_events_before_the_season_date(self):
        """Checks that events past the end of seasons don't contribute score."""
        self.event.date = SEASON_2024.start_date
        self.event.date -= datetime.timedelta(days=1)
        self.event.save()
        for _ in range(10):
            ResultFactory(event=self.event)
        scores = self.compute_scores()
        self.assertFalse(any(score.total_score > 0 for score in scores.values()))

    def test_category_other_does_not_contribute_score(self):
        self.event.category = Event.Category.OTHER
        self.event.save()
        ResultFactory(event=self.event)
        scores = self.compute_scores()
        self.assertEqual(
            0, len(scores), "Events with category 'OTHER' should not count."
        )


class ScoresWithTop8TestCase(TestCase):
    def setUp(self):
        self.event = Event2024Factory()
        self.player = PlayerFactory()

    def score(self, points, result):
        ep = Result(
            points=points,
            event=self.event,
            player=self.player,
            playoff_result=result,
            ranking=1,
        )
        return ScoreMethod2024._qps_for_result(
            ep, event_size=32, has_top_8=True, total_rounds=6
        )

    def test_premier_event(self):
        self.event.category = Event.Category.PREMIER
        self.event.save()
        testCases = [
            (Result.PlayoffResult.WINNER, 400),
            (Result.PlayoffResult.FINALIST, 240),
            (Result.PlayoffResult.SEMI_FINALIST, 160),
            (Result.PlayoffResult.QUARTER_FINALIST, 120),
        ]

        for ranking, points in testCases:
            with self.subTest(f"{ranking.label}"):
                wantScore = (10 + 3) * 6 + points
                gotScore = self.score(10, ranking)
                self.assertEqual(wantScore, gotScore)

    def test_regional_event(self):
        self.event.category = Event.Category.REGIONAL
        self.event.save()
        testCases = [
            (Result.PlayoffResult.WINNER, 100),
            (Result.PlayoffResult.FINALIST, 60),
            (Result.PlayoffResult.SEMI_FINALIST, 40),
            (Result.PlayoffResult.QUARTER_FINALIST, 30),
        ]

        for ranking, points in testCases:
            with self.subTest(f"{ranking.label}"):
                wantScore = (10 + 3) * 4 + points
                gotScore = self.score(10, ranking)
                self.assertEqual(wantScore, gotScore)

    def test_regular_event(self):
        self.event.category = Event.Category.REGULAR
        self.event.save()
        testCases = [
            (Result.PlayoffResult.WINNER, 0),
            (Result.PlayoffResult.FINALIST, 0),
            (Result.PlayoffResult.SEMI_FINALIST, 0),
            (Result.PlayoffResult.QUARTER_FINALIST, 0),
        ]

        for ranking, points in testCases:
            with self.subTest(f"{ranking.label}"):
                wantScore = (10 + 3) + points
                gotScore = self.score(10, ranking)
                self.assertEqual(wantScore, gotScore)


class ScoresWithMatchPointRateTestCase(TestCase):
    def setUp(self):
        self.event = Event2024Factory()
        self.player = PlayerFactory()

    def score(self, points, total_rounds):
        ep = Result(
            points=points,
            event=self.event,
            player=self.player,
            playoff_result=None,
            ranking=1,
        )
        return ScoreMethod2024._qps_for_result(
            ep, event_size=32, has_top_8=True, total_rounds=total_rounds
        )

    def test_premier_event_70_mpr(self):
        self.event.category = Event.Category.PREMIER
        self.event.save()
        test_cases = [(6, 13), (7, 15), (8, 17)]
        for total_rounds, match_points in test_cases:
            with self.subTest(f"70% match point rate with {total_rounds} rounds"):
                extra_score = 60
                base_score = (match_points + 3) * 6
                want_score = base_score + extra_score
                got_score = self.score(match_points, total_rounds)
                self.assertEqual(want_score, got_score)

                # Check that less match points gives less score
                extra_score = 30
                want_score = base_score - 6 + extra_score
                got_score = self.score(match_points - 1, total_rounds)
                self.assertEqual(want_score, got_score)

    def test_premier_event_65_mpr(self):
        self.event.category = Event.Category.PREMIER
        self.event.save()
        test_cases = [(6, 12), (7, 14), (8, 16)]
        for total_rounds, match_points in test_cases:
            with self.subTest(f"70% match point rate with {total_rounds} rounds"):
                extra_score = 30
                base_score = (match_points + 3) * 6
                want_score = base_score + extra_score
                got_score = self.score(match_points, total_rounds)
                self.assertEqual(want_score, got_score)

                # Check that less match points gives less score
                want_score = base_score - 6
                got_score = self.score(match_points - 1, total_rounds)
                self.assertEqual(want_score, got_score)

    def test_regional_event_70_mpr(self):
        self.event.category = Event.Category.REGIONAL
        self.event.save()
        test_cases = [(6, 13), (7, 15), (8, 17)]
        for total_rounds, match_points in test_cases:
            with self.subTest(f"70% match point rate with {total_rounds} rounds"):
                extra_score = 20
                base_score = (match_points + 3) * 4
                want_score = base_score + extra_score
                got_score = self.score(match_points, total_rounds)
                self.assertEqual(want_score, got_score)

                # Check that less match points gives less score
                extra_score = 10
                want_score = base_score - 4 + extra_score
                got_score = self.score(match_points - 1, total_rounds)
                self.assertEqual(want_score, got_score)

    def test_regional_event_65_mpr(self):
        self.event.category = Event.Category.REGIONAL
        self.event.save()
        test_cases = [(6, 12), (7, 14), (8, 16)]
        for total_rounds, match_points in test_cases:
            with self.subTest(f"65% match point rate with {total_rounds} rounds"):
                extra_score = 10
                base_score = (match_points + 3) * 4
                want_score = base_score + extra_score
                got_score = self.score(match_points, total_rounds)
                self.assertEqual(want_score, got_score)

                # Check that less match points gives less score
                want_score = base_score - 4
                got_score = self.score(match_points - 1, total_rounds)
                self.assertEqual(want_score, got_score)


class TestSortResults(TestCase):
    def test_can_order_basic_player_results(self):
        """Checks that we get players ordered correctly."""
        e = Event2024Factory()
        for i in range(10):
            Result.objects.create(
                player=PlayerFactory(),
                ranking=10 - i,
                points=5,
                event=e,
                win_count=1,
                draw_count=2,
                loss_count=0,
            )

        sorted_rankings = [s.ranking for s in sorted(Result.objects.all())]
        self.assertEqual(list(range(1, 11)), sorted_rankings)

    def test_can_order_results_based_on_playoff_results(self):
        e = Event2024Factory(category=Event.Category.PREMIER)
        num_players = 16
        results = [
            Result.objects.create(
                player=PlayerFactory(),
                ranking=i + 1,
                points=3 * (num_players - i),
                event=e,
                win_count=num_players - i,
                draw_count=0,
                loss_count=0,
            )
            for i in range(num_players)
        ]

        # We invert the order of the top 8 players with the single elimination results
        inverse_top_8_results = [results[7], results[6]] + results[4:6] + results[:4]
        for i, r in enumerate(inverse_top_8_results, 1):
            if i == 1:
                r.playoff_result = Result.PlayoffResult.WINNER
            elif i == 2:
                r.playoff_result = Result.PlayoffResult.FINALIST
            elif i <= 4:
                r.playoff_result = Result.PlayoffResult.SEMI_FINALIST
            elif i <= 8:
                r.playoff_result = Result.PlayoffResult.QUARTER_FINALIST
            r.save()

        sorted_rankings = sorted(Result.objects.all())
        self.assertEqual(inverse_top_8_results, sorted_rankings[:8])
        self.assertEqual(results[8:], sorted_rankings[8:])


def create_test_tournament(
    players, category=Event.Category.PREMIER, with_top8=True, **kwargs
):
    event = Event2024Factory(category=category, **kwargs)
    num_players = len(players)
    for i, player in enumerate(players):
        rank = i + 1

        if category != Event.Category.REGULAR and with_top8:
            if rank == 1:
                playoff_result = Result.PlayoffResult.WINNER
            elif rank == 2:
                playoff_result = Result.PlayoffResult.FINALIST
            elif rank <= 4:
                playoff_result = Result.PlayoffResult.SEMI_FINALIST
            elif rank <= 8:
                playoff_result = Result.PlayoffResult.QUARTER_FINALIST
            else:
                playoff_result = None

        ResultFactory(
            player=player,
            points=num_players - i,
            ranking=rank,
            playoff_result=playoff_result,
            event=event,
        )
    return event


class TestScoresByes(TestCase):
    def compute_scores(self):
        return compute_scores(SEASON_2024)

    def test_top_byes(self):
        num_players = 50
        players = [PlayerFactory() for _ in range(num_players)]
        create_test_tournament(players)
        byes = [s.byes for s in self.compute_scores().values()]
        want_byes = [1] * 4 + [0] * (num_players - 4)
        self.assertEqual(want_byes, byes)

    def test_reward_byes(self):
        event = Event2024Factory()
        for i in range(4):
            ResultFactory(event=event, points=1000, ranking=i + 1)

        result5 = ResultFactory(
            points=0,
            ranking=1,
            event=event,
        )
        byes = [s.byes for s in self.compute_scores().values()]
        want_byes = [1] * 4 + [0]
        self.assertEqual(want_byes, byes)
        SpecialRewardFactory(byes=1, result=result5)
        byes = [s.byes for s in self.compute_scores().values()]
        want_byes = [1] * 5
        self.assertEqual(want_byes, byes)


class TestScoresQualified(TestCase):
    def setUp(self):
        self.num_qualified = ScoreMethod2024.TOTAL_QUALIFICATION_SLOTS

    def compute_scores(self):
        return compute_scores(SEASON_2024)

    def assert_qualifications(self, num_players, num_direct=0):
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = (
            [QualificationType.DIRECT] * num_direct
            + [QualificationType.LEADERBOARD] * (self.num_qualified - num_direct)
            + [QualificationType.NONE] * (num_players - self.num_qualified)
        )
        self.assertEqual(want_qualified, got_qualified)

    def test_top_leaderboard_qualified(self):
        num_players = 50
        players = [PlayerFactory() for _ in range(num_players)]

        create_test_tournament(players, category=Event.Category.REGIONAL)
        self.assert_qualifications(num_players)

    def test_direct_qualification(self):
        num_players = 50
        players = [PlayerFactory() for _ in range(num_players)]

        # Create premier event with 40 or more players, so that the winner gets a direct qualification
        create_test_tournament(players)
        self.assert_qualifications(num_players, num_direct=1)

    def test_player_multiple_direct_qualifications(self):
        num_players = 50
        players = [PlayerFactory() for _ in range(num_players)]

        # Let the same player win both Premier events, and the invite should be passed to the next player
        create_test_tournament(players)
        create_test_tournament(players)
        self.assert_qualifications(num_players, num_direct=2)

    def test_trickle_down_to_second_in_second_event(self):
        """Checks that the invite trickles down to the second place on the second event."""
        num_players = 50
        winner = PlayerFactory()
        event1_players = [winner] + [PlayerFactory() for _ in range(num_players)]
        event2_players = [winner] + [PlayerFactory() for _ in range(num_players)]
        create_test_tournament(event1_players, date=datetime.date(2024, 1, 1))
        create_test_tournament(event2_players, date=datetime.date(2024, 2, 1))

        scores = self.compute_scores()

        self.assertEqual(
            scores[event2_players[1].id].qualification_type, QualificationType.DIRECT
        )

    def test_direct_qualification_outside_top_leaderboard(self):
        num_players = 60
        players = [PlayerFactory() for _ in range(num_players)]

        # Create lots of points for all players except one
        event = Event2024Factory(category=Event.Category.REGIONAL)
        [
            ResultFactory(player=player, points=1000, event=event)
            for player in players[1:]
        ]

        # Create a premier event where the player with no previous results/points wins
        create_test_tournament(players)
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        # The last ranked player should get the direct inivte and the other invites go to the top players
        want_qualified = (
            [QualificationType.LEADERBOARD] * (self.num_qualified - 1)
            + [QualificationType.NONE] * (num_players - self.num_qualified)
            + [QualificationType.DIRECT]
        )
        self.assertEqual(want_qualified, got_qualified)

    def test_reward_qualifications(self):
        event = Event2024Factory()
        result = ResultFactory(
            points=3,
            ranking=5,
            event=event,
        )
        SpecialRewardFactory(direct_invite=True, result=result)
        qualifications = [s.qualification_type for s in self.compute_scores().values()]
        want_qualifications = [QualificationType.DIRECT]
        self.assertEqual(want_qualifications, qualifications)


class TestQualificationReason(TestCase):
    def compute_scores(self):
        return compute_scores(SEASON_2024)

    def test_direct_qualification_reason(self):
        num_players = 40
        players = [PlayerFactory() for _ in range(num_players)]

        event = create_test_tournament(players)
        direct_score = list(self.compute_scores().values())[0]
        want_reason = f"Direct qualification for 1st place at '{event.name}'"
        self.assertEqual(want_reason, direct_score.qualification_reason)

    @freeze_time("2024-10-31")
    def test_leaderboard_qual_reason_during_season(self):
        ResultFactory(event=Event2024Factory())
        direct_score = list(self.compute_scores().values())[0]
        want_reason = "This place qualifies for the SUL Invitational tournament at the end of the Season"
        self.assertEqual(want_reason, direct_score.qualification_reason)

    @freeze_time("2024-11-08")
    def test_leaderboard_qual_reason_after_season(self):
        ResultFactory(event=Event2024Factory())
        direct_score = list(self.compute_scores().values())[0]
        want_reason = "Qualified for SUL Invitational tournament"
        self.assertEqual(want_reason, direct_score.qualification_reason)


class TestPlayerDetails2024(TestCase):
    def setUp(self):
        self.client = Client()
        self.player = PlayerFactory()
        self.event = Event2024Factory(category=Event.Category.PREMIER)

    def test_player_details_extra_points_edge_case(self):
        # Make sure we have a tournament with many rounds
        ResultFactory(
            player=self.player,
            ranking=1,
            points=10,
            win_count=7,
            loss_count=7,
            draw_count=0,
        )

        # Make sure the event is with top 8
        ResultFactory(
            event=self.event,
            playoff_result=Result.PlayoffResult.QUARTER_FINALIST,
            win_count=6,
            loss_count=0,
            draw_count=0,
        )

        # Create a player outside of top 8 with 65%+ match point rate
        ResultFactory(
            player=self.player,
            event=self.event,
            ranking=1,
            points=12,
            win_count=4,
            loss_count=0,
            draw_count=0,
        )

        response = self.client.get(
            reverse("player_details_by_season", args=[self.player.id, "2024"])
        )

        # Player should get 30 extra points
        expected_qps = 15 * 6 + 30
        self.assertContains(response, f"<td>{expected_qps}</td>")


class TestScore2024(TestCase):
    def test_add(self):
        s1 = ScoreMethod2024.Score(qps=1, byes=1)
        s2 = ScoreMethod2024.Score(qps=2, byes=1)
        r = s1 + s2
        self.assertEqual(ScoreMethod2024.Score(qps=3, byes=2), r)
