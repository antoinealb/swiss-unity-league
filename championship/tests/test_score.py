import datetime

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

        self.organizer = EventOrganizerFactory()
        self.event = EventFactory(
            format=Event.Format.LEGACY, ranking_type=Event.RankingType.RANKED
        )

    def _test_compute_score(self, category, player_count, want_score):
        self.event.category = category
        self.event.save()

        for i, p in enumerate(Player.objects.all().order_by("id")[:player_count]):
            EventPlayerResult.objects.create(ranking=i + 1, player=p, event=self.event)

        scores = compute_scores()
        for (i, want) in enumerate(want_score):
            got = scores[i + 1]
            self.assertEqual(want, got, f"Invalid score for player {i+1}")

    def test_compute_score_ranking_mtgr_100_small(self):
        self._test_compute_score(
            category=Event.Category.POINTS_100,
            player_count=15,
            want_score=[100, 70] + [50] * 2 + [30] * 4 + [10] * 7,
        )

    def test_compute_score_ranking_mtgr_100_large(self):
        self._test_compute_score(
            category=Event.Category.POINTS_100,
            player_count=32,
            want_score=[100, 80] + [60] * 2 + [40] * 4 + [20] * 7 + [10] * 17,
        )

    def test_compute_score_ranking_mtgr_250_small(self):
        self._test_compute_score(
            category=Event.Category.POINTS_250,
            player_count=15,
            want_score=[250, 180] + [120] * 2 + [60] * 4 + [10] * 7,
        )

    def test_compute_score_ranking_mtgr_250_medium(self):
        self._test_compute_score(
            category=Event.Category.POINTS_250,
            player_count=31,
            want_score=[250, 200]
            + [160] * 2
            + [120] * 4
            + [80] * 4
            + [40] * 4
            + [10] * 14,
        )

    def test_compute_score_ranking_mtgr_250_large(self):
        self._test_compute_score(
            category=Event.Category.POINTS_250,
            player_count=40,
            want_score=[250, 200]
            + [160] * 2
            + [120] * 4
            + [80] * 4
            + [40] * 4
            + [20] * 4
            + [10] * 20,
        )

    def test_compute_score_ranking_mtgr_500(self):
        self._test_compute_score(
            category=Event.Category.POINTS_500,
            player_count=40,
            want_score=[500, 400]
            + [300] * 2
            + [200] * 4
            + [150] * 4
            + [100] * 4
            + [50] * 4
            + [30] * 4
            + [20] * 4
            + [10] * 12,
        )
