from django.db import models
from django.conf import settings
from django.db.models import Count, F
from django.core.validators import MinValueValidator
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
        max_length=200, help_text="The name of the event as defined by the organizer"
    )
    organizer = models.ForeignKey(EventOrganizer, on_delete=models.PROTECT)
    date = models.DateField(
        help_text="The date of the event. For multi-days event, pick the first day."
    )
    url = models.URLField(help_text="A website for information, ticket sale, etc.")

    class Format(models.TextChoices):
        LEGACY = "LEGACY", "Legacy"
        MODERN = "MODERN", "Modern"
        LIMITED = "LIMITED", "Limited"

    format = models.CharField(max_length=10, choices=Format.choices)

    class Category(models.TextChoices):
        WEEKLY = "WEEKLY", "Weekly event"
        PREMIER = "PREMIER", "Premier Event"

    category = models.CharField(max_length=10, choices=Category.choices)
    multiplier = models.PositiveIntegerField(default=1)

    round_count = models.IntegerField(
        help_text="Number of rounds played in the tournament",
        validators=[MinValueValidator(3, "Not enough rounds (min 3)")],
    )

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

    points = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of points, for fixed-rounds tournaments.",
    )
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)


def compute_scores():
    def _participation_points(round_count):
        if round_count >= 5:
            return 2
        elif round_count == 4:
            return 3
        else:
            return 4

    scores = collections.defaultdict(lambda: 0)
    for result in EventPlayerResult.objects.annotate(
        category=F("event__category"),
        multiplier=F("event__multiplier"),
        round_count=F("event__round_count"),
    ).all():
        if result.category == Event.Category.WEEKLY:
            mult = 1
        else:
            mult = result.multiplier

        # TODO: Handle top 8
        pp = _participation_points(result.round_count)
        scores[result.player_id] += (result.points + pp) * mult

    return dict(scores)
