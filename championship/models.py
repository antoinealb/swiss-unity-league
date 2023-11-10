from dataclasses import dataclass
from typing import Any, Iterable
from django.db import models
from django.conf import settings
from django.db.models import Count, F
from django_bleach.models import BleachField
from django.core.cache import cache
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.dispatch import receiver
from championship.cache_function import cache_function
from auditlog.registry import auditlog
from collections import defaultdict
import datetime
from prometheus_client import Gauge, Summary
from django.contrib.humanize.templatetags.humanize import ordinal
import urllib.parse


class Address(models.Model):
    class Meta:
        verbose_name = "Address"

    class Region(models.TextChoices):
        AARGAU = "AG", "Aargau"  # German
        APPENZELL_AUSSERRHODEN = "AR", "Appenzell Ausserrhoden"  # German
        APPENZELL_INNERRHODEN = "AI", "Appenzell Innerrhoden"  # German
        BASEL_LANDSCHAFT = "BL", "Basel-Landschaft"  # German
        BASEL_STADT = "BS", "Basel-Stadt"  # German
        BERN = "BE", "Bern"  # German
        FRIBOURG = "FR", "Fribourg"  # French
        GENEVA = "GE", "Genève"  # French
        GLARUS = "GL", "Glarus"  # German
        GRAUBUNDEN = "GR", "Graubünden"  # German
        JURA = "JU", "Jura"  # French
        LUCERNE = "LU", "Luzern"  # German
        NEUCHATEL = "NE", "Neuchâtel"  # French
        NIDWALDEN = "NW", "Nidwalden"  # German
        OBWALDEN = "OW", "Obwalden"  # German
        SCHAFFHAUSEN = "SH", "Schaffhausen"  # German
        SCHWYZ = "SZ", "Schwyz"  # German
        SOLOTHURN = "SO", "Solothurn"  # German
        ST_GALLEN = "SG", "Sankt Gallen"  # German
        THURGAU = "TG", "Thurgau"  # German
        TICINO = "TI", "Ticino"  # Italian
        URI = "UR", "Uri"  # German
        VALAIS = "VS", "Valais"  # French
        VAUD = "VD", "Vaud"  # French
        ZUG = "ZG", "Zug"  # German
        ZURICH = "ZH", "Zürich"  # German
        FREIBURG_DE = "FR_DE", "Freiburg im Breisgau (DE)"  # German

    class Country(models.TextChoices):
        SWITZERLAND = "CH", "Switzerland"
        AUSTRIA = "AT", "Austria"
        GERMANY = "DE", "Germany"
        ITALY = "IT", "Italy"
        LIECHTENSTEIN = "LI", "Liechtenstein"
        FRANCE = "FR", "France"

    location_name = models.CharField(max_length=255)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=10)
    region = models.CharField(
        max_length=5,
        choices=Region.choices,
        default=Region.ZURICH,
    )
    country = models.CharField(
        max_length=2, choices=Country.choices, default=Country.SWITZERLAND
    )

    organizer = models.ForeignKey(
        "EventOrganizer", on_delete=models.CASCADE, related_name="addresses"
    )

    def get_delete_url(self):
        return reverse("address_delete", args=[self.pk])

    def get_absolute_url(self):
        return reverse("address_edit", args=[self.pk])

    def __str__(self):
        address_parts = (
            [
                self.location_name,
                self.street_address,
                f"{self.postal_code} {self.city}",
            ]
            + self._get_region_as_list()
            + self._get_country_as_list()
        )
        return ", ".join(address_parts)

    def get_seo_address(self):
        address_parts = [
            self.street_address,
            self.city,
            self.postal_code,
            self.get_country_display(),
        ]
        return ", ".join(address_parts)

    def _get_region_as_list(self):
        """Gets the region if it's different from the city.
        We return it in a list, because it's easier to process it further."""
        region = self.get_region_display()
        return [region] if self.city != region else []

    def _get_country_as_list(self):
        """Gets the country if it's different from Switzerland.
        We return it in a list, because it's easier to process it further."""
        country = self.get_country_display()
        return [country] if self.country != Address.Country.SWITZERLAND else []

    def short_string(self):
        """A short string of the address only containing city, region and country."""
        address_parts = (
            [self.city] + self._get_region_as_list() + self._get_country_as_list()
        )
        return ", ".join(address_parts)

    def sort_key(self):
        return (
            self.country != Address.Country.SWITZERLAND,
            self.get_country_display().lower(),
            self.get_region_display().lower(),
            self.city.lower(),
        )

    def __lt__(self, other):
        return self.sort_key() < other.sort_key()

    def get_google_maps_url(self):
        """Return a URL for this address on Google Maps."""
        query = urllib.parse.quote(self.__str__())
        return f"https://www.google.com/maps/search/?api=1&query={query}"


class EventOrganizer(models.Model):
    """
    An organizer, who organizes several events in the championship.
    """

    name = models.CharField(max_length=200)
    contact = models.EmailField(
        help_text="Prefered contact email (not visible to players)"
    )
    description = BleachField(
        help_text="Supports the following HTML tags: {}".format(
            ", ".join(settings.BLEACH_ALLOWED_TAGS)
        ),
        blank=True,
        strip_tags=True,
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    default_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True
    )

    def get_absolute_url(self):
        return reverse("organizer_details", args=[self.pk])

    def get_addresses(self):
        return self.addresses.all()

    def __str__(self):
        return self.name


class EventManager(models.Manager):
    def available_for_result_upload(self, user):
        today = datetime.date.today()
        start_date = today - settings.EVENT_MAX_AGE_FOR_RESULT_ENTRY
        end_date = today
        initial_qs = (
            self.filter(organizer__user=user, date__gte=start_date, date__lte=end_date)
            .annotate(result_cnt=Count("eventplayerresult"))
            .filter(result_cnt=0)
        )

        valid_event_ids = [event.id for event in initial_qs if event.can_be_edited()]
        return initial_qs.filter(id__in=valid_event_ids)


class Event(models.Model):
    """
    A single tournament in the tournament.

    If an organizer hosts several tournaments inside a larger event, each of
    the sub-events will have one Event.

    Events have two different types of ranking: point-based, with a fixed
    number of rounds, or ranking based, typically with a cut to top8.
    """

    class Meta:
        verbose_name = "Event"

    name = models.CharField(
        max_length=200, help_text="The name of this event, e.g. 'Christmas Modern 1k'"
    )
    organizer = models.ForeignKey(EventOrganizer, on_delete=models.PROTECT)
    date = models.DateField(
        help_text="The date of the event. For multi-days event, pick the first day."
    )
    start_time = models.TimeField(
        null=True, blank=True, help_text="Time when the event begins (optional)"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Approximate time when the event ends (optional)",
    )
    url = models.URLField(
        "Website",
        help_text="A website for information, ticket sale, etc.",
        blank=True,
        null=True,
    )
    description = BleachField(
        help_text="Supports the following HTML tags: {}".format(
            ", ".join(settings.BLEACH_ALLOWED_TAGS)
        ),
        blank=True,
        strip_tags=True,
    )
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Format(models.TextChoices):
        LEGACY = "LEGACY", "Legacy"
        LIMITED = "LIMITED", "Limited"
        MODERN = "MODERN", "Modern"
        PIONEER = "PIONEER", "Pioneer"
        STANDARD = "STANDARD", "Standard"
        DUEL_COMMANDER = "DC", "Duel Commander"
        PAUPER = "PAUPER", "Pauper"
        OLD_SCHOOL = "OS", "Old School"
        PRE_MODERN = "PM", "Premodern"

    format = models.CharField(
        max_length=10,
        choices=Format.choices,
    )

    class Category(models.TextChoices):
        REGULAR = "REGULAR", "SUL Regular"
        REGIONAL = "REGIONAL", "SUL Regional"
        PREMIER = "PREMIER", "SUL Premier"

    category = models.CharField(max_length=10, choices=Category.choices)
    decklists_url = models.URLField(
        "Decklists URL",
        help_text="A link to a page containing decklists for the event, for example mtgtop8",
        blank=True,
        null=True,
    )

    results_validation_enabled = models.BooleanField(
        help_text="Whether results will be validated for coherency before being stored.",
        default=True,
    )

    def __str__(self):
        return f"{self.name} - {self.date} ({self.get_category_display()})"

    def get_time_range_display(self) -> str:
        def format_time_24h(t: datetime.time) -> str:
            return t.strftime("%H:%M") if t else ""

        start_time_str = format_time_24h(self.start_time)
        end_time_str = format_time_24h(self.end_time)

        if start_time_str and end_time_str:
            return f"{start_time_str} - {end_time_str}"
        elif start_time_str:
            return f"{start_time_str}"
        else:
            return ""

    def get_delete_url(self):
        return reverse("event_delete", args=[self.pk])

    def get_absolute_url(self):
        return reverse("event_details", args=[self.id])

    def get_icon_url(self):
        return f"types/icons/{self.category.lower()}.png"

    def can_have_top8(self) -> bool:
        return self.category != Event.Category.REGULAR

    def can_be_edited(self) -> bool:
        """Returns whether changing scores for this Event is allowed.

        A TO can edit the event when all of the following conditions are met:
        -The event is not older than settings.EVENT_MAX_AGE_FOR_RESULT_ENTRY
        -The end of season deadline hasn't passed.
        """
        today = datetime.date.today()
        oldest_allowed = today - settings.EVENT_MAX_AGE_FOR_RESULT_ENTRY
        if self.date < oldest_allowed:
            return False

        season = find_current_season(self.date)
        if not season:
            return False

        return season.can_enter_results(today)

    def can_be_deleted(self) -> bool:
        """Events can be deleted if they can still be edited or have no results."""
        return self.can_be_edited() or not self.eventplayerresult_set.exists()

    objects = EventManager()


class LeaderBoardPlayerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(hidden_from_leaderboard=False)


class Player(models.Model):
    """
    Represents a player in the championship, among many tournaments.
    """

    # This used to be first_name, last_name in two separate fields.
    # See https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/
    # for why this was not a good idea.
    name = models.CharField(max_length=200)
    events = models.ManyToManyField(Event, through="EventPlayerResult")
    email = models.EmailField(max_length=254, blank=True)

    hidden_from_leaderboard = models.BooleanField(
        help_text="If true, this should be hidden from the global leaderboard. Useful for virtual players, such as Eventlink's REDACTED.",
        default=False,
    )

    objects = models.Manager()
    leaderboard_objects = LeaderBoardPlayerManager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("player_details", args=[self.id])


class PlayerAlias(models.Model):
    """
    Sometimes players get named in a strange way, or with a typo, or something.
    For example, a player might be named 'Antoine Albertelli', but one TO has
    him as 'antoinealb' (a nickname).
    """

    name = models.CharField(max_length=200)
    true_player = models.ForeignKey(Player, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} (-> {self.true_player})"

    class Meta:
        verbose_name_plural = "player aliases"


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
    win_count = models.PositiveIntegerField(help_text="Number of won matches")
    loss_count = models.PositiveIntegerField(help_text="Number of lost matches")
    draw_count = models.PositiveIntegerField(help_text="Number of drawn matches")

    migrated_from_points_to_record = models.BooleanField(
        default=False,
        help_text="Indicates whether this result was automatically migrated from points to records. Used for diagnostics.",
    )

    class Meta:
        indexes = [models.Index(fields=["event"])]

    def __str__(self):
        score = f"{self.win_count}-{self.loss_count}-{self.draw_count}"
        return f"{self.player.name}@{self.event.name} ({score})"

    def __lt__(self, other):
        """Comparison function for sorting.

        First checks single elimination results, then swiss rounds ranking.
        """
        self_single_elim = self.single_elimination_result or 32
        other_single_elim = other.single_elimination_result or 32
        if self_single_elim < other_single_elim:
            return True
        elif self_single_elim > other_single_elim:
            return False

        return self.ranking < other.ranking

    def get_ranking_display(self):
        SINGLE_ELIM_TO_RANK = {
            EventPlayerResult.SingleEliminationResult.WINNER: "1st",
            EventPlayerResult.SingleEliminationResult.FINALIST: "2nd",
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST: "3rd-4th",
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST: "5th-8th",
        }
        if self.single_elimination_result:
            return SINGLE_ELIM_TO_RANK[self.single_elimination_result]
        else:
            return ordinal(self.ranking)

    def get_record_display(self):
        return f"{self.win_count} - {self.loss_count} - {self.draw_count}"


@dataclass
class Score:
    total_score: int
    rank: int
    byes: int
    qualified: bool


class ScoreMethod2023:
    MULT = {
        Event.Category.REGULAR: 1,
        Event.Category.REGIONAL: 4,
        Event.Category.PREMIER: 6,
    }
    PARTICIPATION_POINTS = 3
    POINTS_FOR_TOP = {
        Event.Category.PREMIER: {
            EventPlayerResult.SingleEliminationResult.WINNER: 500,
            EventPlayerResult.SingleEliminationResult.FINALIST: 300,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST: 200,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST: 150,
        },
        Event.Category.REGIONAL: {
            EventPlayerResult.SingleEliminationResult.WINNER: 100,
            EventPlayerResult.SingleEliminationResult.FINALIST: 60,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST: 40,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST: 30,
        },
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

    @classmethod
    def qps_for_result(
        cls,
        result: EventPlayerResult,
        event_size: int,
        has_top_8: bool,
    ) -> int:
        """
        Returns how many QPs a player got in a single event.
        """
        category = result.event.category
        points = result.points + cls.PARTICIPATION_POINTS
        points = points * cls.MULT[category]

        if result.single_elimination_result:
            points += cls.POINTS_FOR_TOP[category][result.single_elimination_result]
        elif has_top_8:
            # For large tournaments, we award points for placing, even outside of
            # top8. See the rules for explanation
            if event_size > 32 and 9 <= result.ranking <= 12:
                points += cls.POINTS_TOP_9_12[category]
            elif event_size > 48 and 13 <= result.ranking <= 16:
                points += cls.POINTS_TOP_13_16[category]
            elif result.ranking <= 8:
                # If we are in this case, it means the event did not play a top8,
                # only a top4, and we still need to award points for 5th-8th.
                points += cls.POINTS_FOR_TOP[category][
                    EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST
                ]

        return points

    @classmethod
    def byes_for_result(
        cls,
        result: EventPlayerResult,
        event_size: int,
        has_top_8: bool,
    ) -> int:
        """Returns how many byes a given result gives."""
        MIN_SIZE_EXTRA_BYE = 128
        if (
            result.event_size > MIN_SIZE_EXTRA_BYE
            and result.event.category == Event.Category.PREMIER
            and result.single_elimination_result
            == EventPlayerResult.SingleEliminationResult.WINNER
        ):
            return 2
        return 0

    @classmethod
    def _byes_for_rank(cls, rank: int) -> int:
        if rank <= 1:
            return 2
        elif rank <= 5:
            return 1
        else:
            return 0

    MAX_BYES = 2

    @classmethod
    def finalize_scores(
        cls, scores_by_player: dict[int, int], byes_per_player: dict[int, int]
    ) -> dict[int, Score]:
        """Implements the last step of score processing.

        This function takes a list of (player_id, score) tuples and turns it
        into a sequence of Score objects, checking the maximum number of byes
        and deciding who is qualified and not.

        Returns a dict of (player_id: Score)

        """
        sorted_scores = sorted(
            scores_by_player.items(), key=lambda x: x[1], reverse=True
        )
        scores = {}
        for i, (player, points) in enumerate(sorted_scores):
            rank = i + 1
            byes = cls._byes_for_rank(rank) + byes_per_player[player]
            byes = min(byes, cls.MAX_BYES)

            scores[player] = Score(
                total_score=points,
                rank=rank,
                byes=byes,
                qualified=rank <= 40,
            )

        return scores


def get_results_with_qps(
    event_player_results: models.QuerySet[EventPlayerResult],
) -> Iterable[EventPlayerResult]:
    """
    Pass a QuerySet of EventPlayerResult, and get it annotated with the following fields:
    - has_top8: True if the event has a top8
    - qps: the number of QPs the player got in this event
    - event_size: the number of players in the event
    - event: the event
    - byes: Number of byes awarded for this result.
    """
    results = event_player_results.select_related("event").annotate(
        event_size=Count("event__eventplayerresult"),
        top_count=Count("event__eventplayerresult__single_elimination_result"),
    )

    for result in results:
        result.has_top8 = result.top_count > 0
        result.qps = ScoreMethod2023.qps_for_result(
            result,
            event_size=result.event_size,
            has_top_8=result.has_top8,
        )
        result.byes = ScoreMethod2023.byes_for_result(
            result, event_size=result.event_size, has_top_8=result.has_top8
        )
        yield result


scores_computation_time_seconds = Summary(
    "scores_computation_time_seconds", "Time spent to compute scores of all players"
)


def get_leaderboard():
    scores_by_player = compute_scores()
    players = list(Player.leaderboard_objects.all())
    scores_with_player = []
    for player in players:
        score = scores_by_player.get(player.id)
        if score:
            player.score = score
            scores_with_player.append(player)
    scores_with_player.sort(key=lambda l: l.score.rank)
    return scores_with_player


@cache_function(cache_key="compute_scores")
@scores_computation_time_seconds.time()
def compute_scores():
    players_reaching_max = 0

    scores_by_player: defaultdict[int, Any] = defaultdict(lambda: 0)
    extra_byes_by_player: defaultdict[int, int] = defaultdict(lambda: 0)

    for result in get_results_with_qps(
        EventPlayerResult.objects.filter(
            event__date__lte=settings.SEASON_MAP[settings.DEFAULT_SEASON_ID].end_date
        ).filter(player__in=Player.leaderboard_objects.all())
    ):
        scores_by_player[result.player_id] += result.qps
        extra_byes_by_player[result.player_id] += result.byes

    return ScoreMethod2023.finalize_scores(scores_by_player, extra_byes_by_player)


@receiver(post_delete, sender=EventPlayerResult)
@receiver(pre_save, sender=EventPlayerResult)
def invalidate_score_cache(sender, **kwargs):
    cache.delete("compute_scores")


def find_current_season(date: datetime.date):
    for id, season in settings.SEASON_MAP.items():
        if season.start_date <= date <= season.end_date:
            return season


auditlog.register(EventOrganizer)
auditlog.register(Player, m2m_fields={"events"})
auditlog.register(Event)
auditlog.register(EventPlayerResult)
