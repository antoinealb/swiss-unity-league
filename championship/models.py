from django.db import models
from django.conf import settings
from django.db.models import Count
from django_bleach.models import BleachField
from django.urls import reverse
from auditlog.registry import auditlog
from championship.season import find_season_by_date, Season
import datetime
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
        VINTAGE = "VINTAGE", "Vintage"

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

    def get_category_icon_url(self):
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

        season = find_season_by_date(self.date)
        if not season:
            return False

        return season.can_enter_results(today)

    @property
    def season(self) -> Season:
        return find_season_by_date(self.date)

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

    deck_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of the player's deck, e.g. 'UW Control'",
    )

    decklist_url = models.URLField(
        "Decklist Link",
        help_text="Link to a page where the decklist of the player can be viewed.",
        blank=True,
        null=True,
    )

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


auditlog.register(EventOrganizer)
auditlog.register(Player, m2m_fields={"events"})
auditlog.register(Event)
auditlog.register(EventPlayerResult)
