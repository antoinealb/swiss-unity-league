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

        for _ in range(50):
            PlayerFactory()

        self.event = EventFactory()

    def _test_compute_score(self, category, points, want_score):
        player_count = len(points)
        self.event.category = category
        self.event.save()

        players = Player.objects.all().order_by("id")[:player_count]
        for i, (player, pi) in enumerate(zip(players, points)):
            EventPlayerResult.objects.create(
                player=player,
                event=self.event,
                points=pi,
            )

        scores = compute_scores()
        for (i, want) in enumerate(want_score):
            got = scores[i + 1]
            self.assertEqual(want, got, f"Invalid score for player {i+1}")

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
            self.assertEqual(0, score, f"Unexpected points for player {player_id}")

    def test_max_500_points_for_regular(self):
        """The league rules stipulate that the maximum amount of points a
        player can get from regular eents is 500. The number of points in other
        categories is not limited."""
        player = PlayerFactory()

        # First, reach the cap of 500 points for REGULAR
        for _ in range(6):
            e = EventFactory(category=Event.Category.REGULAR)
            EventPlayerResult.objects.create(
                player=player,
                event=e,
                points=100,
            )

        # Then create an additional event
        e = EventFactory(category=Event.Category.PREMIER)
        EventPlayerResult.objects.create(
            player=player,
            event=e,
            points=10,
        )

        scores = compute_scores()
        self.assertEqual(578, scores[player.id])


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
        )
        return qps_for_result(ep, category)

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


class TestSafetyChecks(TestCase):
    def test_cannot_create_events_with_less_than_3_rounds(self):
        with self.assertRaises(ValidationError):
            e = EventFactory()
            e.full_clean()
