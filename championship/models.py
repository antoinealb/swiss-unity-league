from django.db import models
from django.conf import settings
from django.db.models import Count, F
from django.core.validators import MinValueValidator
from django_bleach.models import BleachField
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import bleach
import collections


class EventOrganizer(models.Model):
    """
    An organizer, who organizes several events in the championship.
    """

    name = models.CharField(max_length=200)
    contact = models.EmailField(help_text="Prefered contact email")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return self.name


class Event(models.Model):
    """
    A single tournament in the tournament.

    If an organizer hosts several tournaments inside a larger event, each of
    the sub-events will have one Event.

    Events have two different types of ranking: point-based, with a fixed
    number of rounds, or ranking based, typically with a cut to top8.
    """

    name = models.CharField(
        max_length=200, help_text="The name of this event, e.g. 'Christmas Modern 1k'"
    )
    organizer = models.ForeignKey(EventOrganizer, on_delete=models.PROTECT)
    date = models.DateField(
        help_text="The date of the event. For multi-days event, pick the first day."
    )
    url = models.URLField(
        "Website", help_text="A website for information, ticket sale, etc."
    )
    description = BleachField(
        help_text="Supports the following HTML tags: {}".format(
            ", ".join(bleach.ALLOWED_TAGS)
            + "\nYou can copy and paste the description from a website like swissmtg.ch, then HTML syntax will also be copied."
        ),
        blank=True,
        strip_tags=True,
    )

    class Format(models.TextChoices):
        LEGACY = "LEGACY", "Legacy"
        LIMITED = "LIMITED", "Limited"
        MODERN = "MODERN", "Modern"
        PIONEER = "PIONEER", "Pioneer"
        STANDARD = "STANDARD", "Standard"

    format = models.CharField(
        max_length=10,
        choices=Format.choices,
        help_text="If your desired format is not listed, please contact us and we'll add it.",
    )

    class Category(models.TextChoices):
        REGULAR = "REGULAR", "SUL Regular"
        REGIONAL = "REGIONAL", "SUL Regional"
        PREMIER = "PREMIER", "SUL Premier"

    category = models.CharField(max_length=10, choices=Category.choices)

    def __str__(self):
        return f"{self.name} - {self.date} ({self.get_category_display()})"


class Player(models.Model):
    """
    Represents a player in the championship, among many tournaments.
    """

    # This used to be first_name, last_name in two separate fields.
    # See https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/
    # for why this was not a good idea.
    name = models.CharField(max_length=200)
    events = models.ManyToManyField(Event, through="EventPlayerResult")

    def __str__(self):
        return self.name


class EventPlayerResult(models.Model):
    """
    A result for a single player in a single event.
    """

    class SingleEliminationResult(models.IntegerChoices):
        WINNER = 1
        FINALIST = 2
        SEMI_FINALIST = 4
        QUARTER_FINALIST = 8

    points = models.IntegerField(
        help_text="Number of points scored by that player",
    )
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    single_elimination_result = models.PositiveIntegerField(
        null=True,
        blank=True,
        choices=SingleEliminationResult.choices,
    )
    ranking = models.PositiveIntegerField(help_text="Standings after the Swiss rounds")


def qps_for_result(
    result: EventPlayerResult, category: Event.Category, event_size: int
) -> int:
    """
    Returns how many QPs a player got in a single event.
    """

    MULT = {
        Event.Category.REGULAR: 1,
        Event.Category.REGIONAL: 4,
        Event.Category.PREMIER: 6,
    }
    PARTICIPATION_POINTS = 3
    POINTS_FOR_TOP = {
        (Event.Category.PREMIER, EventPlayerResult.SingleEliminationResult.WINNER): 500,
        (
            Event.Category.PREMIER,
            EventPlayerResult.SingleEliminationResult.FINALIST,
        ): 300,
        (
            Event.Category.PREMIER,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST,
        ): 200,
        (
            Event.Category.PREMIER,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
        ): 150,
        (
            Event.Category.REGIONAL,
            EventPlayerResult.SingleEliminationResult.WINNER,
        ): 100,
        (
            Event.Category.REGIONAL,
            EventPlayerResult.SingleEliminationResult.FINALIST,
        ): 60,
        (
            Event.Category.REGIONAL,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST,
        ): 40,
        (
            Event.Category.REGIONAL,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
        ): 30,
    }
    POINTS_TOP_9_12 = {
        Event.Category.PREMIER: 75,
        Event.Category.REGIONAL: 15,
        Event.Category.REGULAR: 0,
    }
    POINTS_TOP_13_16 = {
        Event.Category.PREMIER: 50,
        Event.Category.REGIONAL: 10,
        Event.Category.REGULAR: 0,
    }

    points = result.points + PARTICIPATION_POINTS
    points = points * MULT[category]

    if result.single_elimination_result:
        # TODO: Top 16 points for events which had a top 8 and more than 32
        # players.
        points += POINTS_FOR_TOP[category, result.single_elimination_result]

    else:
        # For large tournaments, we award points for placing, even outside of
        # top8. See the rules for explanation
        if event_size > 32 and 9 <= result.ranking <= 12:
            points += POINTS_TOP_9_12[category]
        elif event_size > 48 and 13 <= result.ranking <= 16:
            points += POINTS_TOP_13_16[category]

    return points


SCORES_CACHE_KEY = "championship.scores"
REGULAR_MAX_SCORE = 500


def compute_scores():
    res = cache.get(SCORES_CACHE_KEY)

    if res:
        return res

    scores_by_player_category = collections.defaultdict(
        lambda: collections.defaultdict(lambda: 0)
    )

    for result in EventPlayerResult.objects.annotate(
        category=F("event__category"),
        size=Count("event__eventplayerresult"),
    ).all():
        # TODO: Handle top 8
        qps = qps_for_result(result, result.category, result.size)
        scores_by_player_category[result.player_id][result.category] += qps

    scores = dict()
    for player in scores_by_player_category:
        if (
            scores_by_player_category[player][Event.Category.REGULAR]
            > REGULAR_MAX_SCORE
        ):
            scores_by_player_category[player][
                Event.Category.REGULAR
            ] = REGULAR_MAX_SCORE
        scores[player] = sum(scores_by_player_category[player].values())

    cache.set(SCORES_CACHE_KEY, scores, timeout=None)

    return scores


@receiver(post_save, sender=Event)
@receiver(post_save, sender=EventPlayerResult)
@receiver(post_delete, sender=EventPlayerResult)
def invalidate_cache_on_result_changes(*args, **kwargs):
    cache.delete(SCORES_CACHE_KEY)
