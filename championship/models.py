from django.db import models
from django.conf import settings
from django.db.models import Count, F
import collections


class EventOrganizer(models.Model):
    """
    An organizer, who organizes several events in the championship.
    """

    name = models.CharField(max_length=200)
    contact = models.EmailField(help_text="Prefered contact email")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class Event(models.Model):
    """
    A single tournament in the tournament.

    If an organizer hosts several tournaments inside a larger event, each of
    the sub-events will have one Event.

    Events have two different types of ranking: point-based, with a fixed
    number of rounds, or ranking based, typically with a cut to top8.
    """

    class Format(models.TextChoices):
        LEGACY = "LEGACY", "Legacy"
        MODERN = "MODERN", "Modern"
        LIMITED = "LIMITED", "Limited"

    class RankingType(models.TextChoices):
        ROUNDS = "ROUNDS", "Number of rounds"
        RANKED = "RANKED", "Ranking-based"

    class Category(models.TextChoices):
        POINTS_100 = "100", "100"
        POINTS_250 = "250", "250"
        POINTS_500 = "500", "500"
        POINTS_1000 = "1000", "1000"

    # TODO: Tournament size
    name = models.CharField(max_length=200)
    organizer = models.ForeignKey(EventOrganizer, on_delete=models.PROTECT)
    date = models.DateField()
    url = models.URLField(help_text="A website for information, ticket sale, etc.")
    format = models.CharField(max_length=10, choices=Format.choices)
    category = models.CharField(max_length=4, choices=Category.choices)
    ranking_type = models.CharField(max_length=10, choices=RankingType.choices)
    round_count = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of rounds, only used for tournaments with fixed number of rounds.",
    )


class Player(models.Model):
    """
    Represents a player in the championship, amon many tournaments.
    """

    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    events = models.ManyToManyField(Event, through="EventPlayerResult")


class EventPlayerResult(models.Model):
    """
    A result for a single player in a single event.
    """

    ranking = models.IntegerField(
        blank=True,
        null=True,
        help_text="Ranking, for tournaments where a ranking result is used.",
    )
    points = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of points, for fixed-rounds tournaments.",
    )
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)


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
            scores[result.player_id] += 10
        else:
            scores[result.player_id] += points[result.ranking - 1]

    return dict(scores)
