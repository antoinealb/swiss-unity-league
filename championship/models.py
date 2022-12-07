from django.db import models
from django.conf import settings
from django.db.models import Count, F
from django.core.validators import MinValueValidator
from django_bleach.models import BleachField
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

    format = models.CharField(max_length=10, choices=Format.choices)

    class Category(models.TextChoices):
        REGULAR = "REGULAR", "SUL Regular"
        REGIONAL = "REGIONAL", "SUL Regional"
        PREMIER = "PREMIER", "SUL Premier"

    category = models.CharField(max_length=10, choices=Category.choices)

    def __str__(self):
        return f"{self.name} - {self.date} ({self.get_category_display()})"


class Player(models.Model):
    """
    Represents a player in the championship, amon many tournaments.
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
        choices=SingleEliminationResult.choices,
    )


def qps_for_result(result: EventPlayerResult, category: Event.Category) -> int:
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

    points = result.points + PARTICIPATION_POINTS
    points = points * MULT[category]

    if result.single_elimination_result:
        # TODO: Top 16 points for events which had a top 8 and more than 32
        # players.
        points += POINTS_FOR_TOP[category, result.single_elimination_result]

    return points


def compute_scores():
    scores = collections.defaultdict(lambda: 0)
    for result in EventPlayerResult.objects.annotate(
        category=F("event__category"),
    ).all():
        # TODO: Handle top 8
        scores[result.player_id] += qps_for_result(result, result.category)

    return dict(scores)
