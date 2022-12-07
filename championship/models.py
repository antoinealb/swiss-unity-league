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
        max_length=200, help_text="The name of this event, e.g. 'Christmas Modern 1k'"
    )
    organizer = models.ForeignKey(EventOrganizer, on_delete=models.PROTECT)
    date = models.DateField(
        help_text="The date of the event. For multi-days event, pick the first day."
    )
    url = models.URLField(
        "Website", help_text="A website for information, ticket sale, etc."
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

    points = models.IntegerField(
        help_text="Number of points scored by that player",
    )
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)


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

    res = result.points + PARTICIPATION_POINTS
    res = res * MULT[category]

    return res


def compute_scores():
    scores = collections.defaultdict(lambda: 0)
    for result in EventPlayerResult.objects.annotate(
        category=F("event__category"),
    ).all():
        # TODO: Handle top 8
        scores[result.player_id] += qps_for_result(result, result.category)

    return dict(scores)
