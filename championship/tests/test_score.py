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

    def _test_compute_score(
        self, category, round_count, points, want_score, multiplier=1
    ):
        player_count = len(points)
        self.event.category = category
        self.event.round_count = round_count
        self.event.multiplier = multiplier
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
            category=Event.Category.WEEKLY,
            round_count=3,
            points=[10, 10, 9, 5],
            want_score=[14, 14, 13, 9],
        )

    def test_compute_score_points_weekly_4rounds(self):
        self._test_compute_score(
            category=Event.Category.WEEKLY,
            round_count=4,
            points=[10, 10, 9, 5],
            want_score=[13, 13, 12, 8],
        )

    def test_compute_score_points_weekly_5rounds(self):
        self._test_compute_score(
            category=Event.Category.WEEKLY,
            round_count=5,
            points=[10, 10, 9, 5],
            want_score=[12, 12, 11, 7],
        )

    def test_multiplier(self):
        self._test_compute_score(
            category=Event.Category.PREMIER,
            round_count=4,
            multiplier=3,
            points=[10, 10, 9, 5],
            want_score=[39, 39, 36, 24],
        )


class TestSafetyChecks(TestCase):
    def test_cannot_create_events_with_less_than_3_rounds(self):
        with self.assertRaises(ValidationError):
            e = EventFactory(round_count=2)
            e.full_clean()
