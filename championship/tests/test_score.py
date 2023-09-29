import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth.models import User
from django.db.models import Count, F
from faker import Faker

from championship.factories import *
from championship.models import *


class TestComputeScore(TestCase):
    def setUp(self):
        fake = Faker()

        self.event = EventFactory()

    def _test_compute_score(self, category, points, want_score):
        player_count = len(points)
        self.event.category = category
        self.event.save()

        players = [PlayerFactory() for _ in range(player_count)]
        for i, (player, pi) in enumerate(zip(players, points)):
            EventPlayerResult.objects.create(
                player=player,
                event=self.event,
                points=pi,
                ranking=i + 1,
            )

        scores = compute_scores()
        for i, want in enumerate(want_score, 1):
            score = scores[i]
            self.assertEqual(want, score[SCORE_POINTS], f"Invalid score for player {i}")
            self.assertEqual(i, score[SCORE_RANK], f"Invalid rank for player {i}")

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

    def test_ignores_events_with_no_results(self):
        self.event.save()
        scores = compute_scores()
        for player_id, score in scores:
            self.assertEqual(
                0, score[SCORE_POINTS], f"Unexpected points for player {player_id}"
            )

    def test_max_500_points_for_regular(self):
        """The league rules stipulate that the maximum amount of points a
        player can get from regular events is 500. The number of points in other
        categories is not limited."""
        player = PlayerFactory()

        # First, reach the cap of 500 points for REGULAR
        for i in range(6):
            e = EventFactory(category=Event.Category.REGULAR)
            EventPlayerResult.objects.create(
                player=player,
                event=e,
                points=100,
                ranking=i + 1,
            )

        # Then create an additional event
        e = EventFactory(category=Event.Category.PREMIER)
        EventPlayerResult.objects.create(
            player=player,
            event=e,
            points=10,
            ranking=10,
        )

        scores = compute_scores()
        self.assertEqual(578, scores[player.id][SCORE_POINTS])


class ExtraPointsOutsideOfTopsTestCase(TestCase):
    def setUp(self):
        self.event = EventFactory()

    def _test_compute_score(self, category, points):
        player_count = len(points)
        self.event.category = category
        self.event.save()

        players = [PlayerFactory() for _ in range(player_count)]
        for i, (player, pi) in enumerate(zip(players, points)):
            if i == 0:
                ser = EventPlayerResult.SingleEliminationResult.WINNER
            elif i == 1:
                ser = EventPlayerResult.SingleEliminationResult.FINALIST
            elif 2 <= i <= 3:
                ser = EventPlayerResult.SingleEliminationResult.SEMI_FINALIST
            elif i < 8:
                ser = EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST
            else:
                ser = None

            EventPlayerResult.objects.create(
                player=player,
                event=self.event,
                points=pi,
                ranking=i + 1,
                single_elimination_result=ser,
            )

        scores = compute_scores()
        return [scores[p.id][SCORE_POINTS] for p in players]

    def test_extra_points_for_9th_in_large_events(self):
        """Checks that we get some extra points to the 9th player in larger events (more than 32)"""
        points = [10] * 8 + [9] * 4 + [0] * 21
        want_score = [48 + 15] * 4 + [12] * 21
        scores = self._test_compute_score(
            category=Event.Category.REGIONAL,
            points=points,
        )
        self.assertEqual(scores[8:], want_score)

    def test_extra_points_for_9th_in_large_premier(self):
        """Checks that we get some extra points to the 9th player in larger events (more than 32)"""
        # Note that here 9th gets more QPs that top 8 but that's because we did
        # not input the top 8 result with finalists and such yet
        points = [10] * 8 + [9] * 4 + [0] * 21
        want_score = [12 * 6 + 75] * 4 + [18] * 21
        scores = self._test_compute_score(
            category=Event.Category.PREMIER,
            points=points,
        )
        self.assertEqual(scores[8:], want_score)

    def test_extra_points_for_13th_in_xlarge_events(self):
        """Checks that we get some extra points to the 9th player in XL events (more than 48)"""
        points = [10] * 8 + [9] * 4 + [0] * 37
        want_score = [48 + 15] * 4 + [12 + 10] * 4 + [12] * 33
        scores = self._test_compute_score(
            category=Event.Category.REGIONAL,
            points=points,
        )
        self.assertEqual(scores[8:], want_score)

    def test_extra_points_for_13th_in_xlarge_premier(self):
        """Checks that we get some extra points to the 9th player in XL events (more than 48)"""
        points = [10] * 8 + [9] * 4 + [0] * 37
        want_score = [12 * 6 + 75] * 4 + [18 + 50] * 4 + [18] * 33
        scores = self._test_compute_score(
            category=Event.Category.PREMIER,
            points=points,
        )
        self.assertEqual(scores[8:], want_score)

    def test_large_event_no_top_8(self):
        points = [10] * 8 + [9] * 4 + [0] * 37
        want_score = [48] * 4 + [12] * 4 + [12] * 33

        player_count = len(points)
        self.event.category = Event.Category.REGIONAL
        self.event.save()

        players = [PlayerFactory() for _ in range(player_count)]
        # No top 8 results
        for i, (player, pi) in enumerate(zip(players, points)):
            EventPlayerResult.objects.create(
                player=player,
                event=self.event,
                points=pi,
                ranking=i + 1,
            )

        scores = compute_scores()
        points = [scores[p.id][SCORE_POINTS] for p in players]
        self.assertEqual(points[8:], want_score)


class ScoresWithTop8TestCase(TestCase):
    def setUp(self):
        self.event = EventFactory()
        self.player = PlayerFactory()

    def score(self, category, points, result):
        ep = EventPlayerResult(
            points=points,
            event=self.event,
            player=self.player,
            single_elimination_result=result,
            ranking=1,
        )
        return qps_for_result(ep, category, event_size=32, has_top_8=True)

    def test_premier_event(self):
        testCases = [
            (EventPlayerResult.SingleEliminationResult.WINNER, 500),
            (EventPlayerResult.SingleEliminationResult.FINALIST, 300),
            (EventPlayerResult.SingleEliminationResult.SEMI_FINALIST, 200),
            (EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST, 150),
        ]

        for ranking, points in testCases:
            with self.subTest(f"{ranking.label}"):
                wantScore = (10 + 3) * 6 + points
                gotScore = self.score(Event.Category.PREMIER, 10, ranking)
                self.assertEqual(wantScore, gotScore)

    def test_regional_event(self):
        testCases = [
            (EventPlayerResult.SingleEliminationResult.WINNER, 100),
            (EventPlayerResult.SingleEliminationResult.FINALIST, 60),
            (EventPlayerResult.SingleEliminationResult.SEMI_FINALIST, 40),
            (EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST, 30),
        ]

        for ranking, points in testCases:
            with self.subTest(f"{ranking.label}"):
                wantScore = (10 + 3) * 4 + points
                gotScore = self.score(Event.Category.REGIONAL, 10, ranking)
                self.assertEqual(wantScore, gotScore)

    def test_top8_when_only_top4_where_played(self):
        """Tests a scenario where we only played a top4."""
        r = EventPlayerResultFactory(points=10, ranking=5)

        want = (10 + 3) * 6 + 150
        got = qps_for_result(r, Event.Category.PREMIER, 5, has_top_8=True)

        self.assertEqual(want, got)


class TestSortEventPlayerResults(TestCase):
    def test_can_order_basic_player_results(self):
        """Checks that we get players ordered correctly."""
        e = EventFactory()
        for i in range(10):
            EventPlayerResult.objects.create(
                player=PlayerFactory(),
                ranking=10 - i,
                points=5,
                event=e,
            )

        sorted_rankings = [s.ranking for s in sorted(EventPlayerResult.objects.all())]
        self.assertEqual(list(range(1, 11)), sorted_rankings)

    def test_can_order_results_based_on_single_elimination_results(self):
        e = EventFactory(category=Event.Category.PREMIER)
        num_players = 16
        results = [
            EventPlayerResult.objects.create(
                player=PlayerFactory(),
                ranking=i + 1,
                points=num_players - i,
                event=e,
            )
            for i in range(num_players)
        ]

        # We invert the order of the top 8 players with the single elimination results
        inverse_top_8_results = [results[7], results[6]] + results[4:6] + results[:4]
        for i, r in enumerate(inverse_top_8_results, 1):
            if i == 1:
                r.single_elimination_result = (
                    EventPlayerResult.SingleEliminationResult.WINNER
                )
            elif i == 2:
                r.single_elimination_result = (
                    EventPlayerResult.SingleEliminationResult.FINALIST
                )
            elif i <= 4:
                r.single_elimination_result = (
                    EventPlayerResult.SingleEliminationResult.SEMI_FINALIST
                )
            elif i <= 8:
                r.single_elimination_result = (
                    EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST
                )
            r.save()

        sorted_rankings = sorted(EventPlayerResult.objects.all())
        self.assertEqual(inverse_top_8_results, sorted_rankings[:8])
        self.assertEqual(results[8:], sorted_rankings[8:])


def create_test_tournament(players, category=Event.Category.PREMIER, with_top8=True):
    event = EventFactory(category=category)
    num_players = len(players)
    for i, player in enumerate(players):
        rank = i + 1

        if category != Event.Category.REGULAR and with_top8:
            if rank == 1:
                ser = EventPlayerResult.SingleEliminationResult.WINNER
            if rank == 2:
                ser = EventPlayerResult.SingleEliminationResult.FINALIST
            if rank <= 4:
                ser = EventPlayerResult.SingleEliminationResult.SEMI_FINALIST
            if rank <= 8:
                ser = EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST

        EventPlayerResultFactory(
            player=player,
            points=num_players - i,
            ranking=rank,
            single_elimination_result=ser,
            event=event,
        )


class TestScoresByes(TestCase):
    def test_top_byes(self):
        num_players = 50
        players = [PlayerFactory() for _ in range(num_players)]
        create_test_tournament(players)
        byes = [s[SCORE_BYES] for s in compute_scores().values()]
        want_byes = [2] + [1] * 4 + [0] * (num_players - 5)
        self.assertEqual(want_byes, byes)

    def test_large_tournament_byes(self):
        num_players = 130
        players = [PlayerFactory() for _ in range(num_players)]

        create_test_tournament(players)
        # Make sure that a different player is points leader
        EventPlayerResultFactory(
            single_elimination_result=EventPlayerResult.SingleEliminationResult.FINALIST,
            event=EventFactory(category=Event.Category.PREMIER),
            player=players[1],
        )

        # Now the winner and the points leader should both have 2 byes
        byes = [s[SCORE_BYES] for s in compute_scores().values()]
        want_byes = [2] * 2 + [1] * 3 + [0] * (num_players - 5)
        self.assertEqual(want_byes, byes)

        # Change event to regional and winner shouldn't get 2 byes anymore
        Event.objects.update(category=Event.Category.REGIONAL)
        byes = [s[SCORE_BYES] for s in compute_scores().values()]
        want_byes = [2] * 1 + [1] * 4 + [0] * (num_players - 5)
        self.assertEqual(want_byes, byes)

    def test_max_byes(self):
        num_players = 130
        players = [PlayerFactory() for _ in range(num_players)]
        # One person wins 2 large events (hence 4 byes) but maximum byes should still be 2
        create_test_tournament(players)
        create_test_tournament(players)

        # Make sure that a different player is points leader
        for _ in range(4):
            EventPlayerResultFactory(
                single_elimination_result=EventPlayerResult.SingleEliminationResult.FINALIST,
                event=EventFactory(category=Event.Category.PREMIER),
                player=players[1],
            )
        # Now the winner and the points leader should both have 2 byes
        byes = [s[SCORE_BYES] for s in compute_scores().values()]
        want_byes = [2] * 2 + [1] * 3 + [0] * (num_players - 5)
        self.assertEqual(want_byes, byes)


class TestScoresQualified(TestCase):
    def test_top_32_qualified(self):
        num_players = 50
        players = [PlayerFactory() for _ in range(num_players)]
        create_test_tournament(players)
        byes = [s[SCORE_QUALIFIED] for s in compute_scores().values()]
        want_byes = [True] * 32 + [False] * (num_players - 32)
        self.assertEqual(want_byes, byes)
