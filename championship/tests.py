from django.test import TestCase
from .models import *
from faker import Faker
from django.contrib.auth.models import User
from django.db.models import Count, F
import datetime
import collections


class TestComputeScore(TestCase):
    def setUp(self):
        fake = Faker()
        self.players = []
        for _ in range(50):
            first, last = tuple(fake.name().split(" ", maxsplit=1))
            Player.objects.create(first_name=first, last_name=last)

        p = fake.profile()
        self.organizer_user = User.objects.create_user(p["username"], p["mail"], "1234")
        self.organizer = EventOrganizer.objects.create(
            name="TestTO", contact="test@test.com", user=self.organizer_user
        )
        self.event = Event.objects.create(
            name="TestEvent",
            organizer=self.organizer,
            date=datetime.date(2022, 12, 24),
            url="test.com",
            category=Event.Category.POINTS_100,
            format=Event.Format.LEGACY,
            ranking_type=Event.RankingType.RANKED,
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

    def test_compute_score_ranking_mtgr_1000(self):
        self._test_compute_score(
            category=Event.Category.POINTS_1000,
            player_count=40,
            want_score=[1000, 800]
            + [600] * 2
            + [400] * 4
            + [200] * 4
            + [150] * 4
            + [100] * 4
            + [50] * 4
            + [20] * 4
            + [10] * 12,
        )


def _points_for_tournament(category, player_count):
    # TODO: Points-based tournament
    points = {
        Event.Category.POINTS_100: [
            (15, [100, 70, 50, 50, 30, 30, 30, 30]),
            (1000, [100, 80, 60, 60] + [40] * 4 + [20] * 7),
        ],
        Event.Category.POINTS_250: [
            (15, [250, 180, 120, 120, 60, 60, 60, 60]),
            (31, [250, 200, 160, 160] + [120] * 4 + [80] * 4 + [40] * 4),
            (1000, [250, 200, 160, 160] + [120] * 4 + [80] * 4 + [40] * 4 + 4 * [20]),
        ],
        Event.Category.POINTS_500: [
            (
                1000,
                [500, 400, 300, 300]
                + [200] * 4
                + [150] * 4
                + [100] * 4
                + [50] * 4
                + [30] * 4
                + [20] * 4,
            ),
        ],
    }

    for limit, p in points[category]:
        if player_count <= limit:
            return p

    raise ValueError("Could not find a big enough event in category!")


def compute_scores():
    scores = collections.defaultdict(lambda: 0)
    for result in EventPlayerResult.objects.annotate(
        player_count=Count("event__player"),
        category=F("event__category"),
    ).all():
        points = _points_for_tournament(result.category, result.player_count)
        if result.ranking > len(points):
            scores[result.player.id] += 10
        else:
            scores[result.player.id] += points[result.ranking - 1]

    return dict(scores)
