# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import urllib.parse

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import ordinal
from django.core.exceptions import ValidationError
from django.core.validators import validate_image_file_extension
from django.db import models
from django.db.models import Count
from django.urls import reverse

from django_bleach.models import BleachField

from championship.season import Season, find_season_by_date


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
        query = urllib.parse.quote(str(self))
        return f"https://www.google.com/maps/search/?api=1&query={query}"


def organizer_image_validator(image):
    if image.size > 500 * 1024:
        raise ValidationError("Image file too large ( > 500KB )")


class EventOrganizer(models.Model):
    """
    An organizer, who organizes several events in the championship.
    """

    name = models.CharField(max_length=200, verbose_name="Association/Store name")
    contact = models.EmailField(
        verbose_name="Invoice email",
        help_text="If you run SUL Regional or SUL Premier events, you will receive your incoices here.",
    )
    url = models.URLField("Website", blank=True, null=True)
    description = BleachField(
        help_text="Describe your organization to the players. You can also provide links to join your group chats or follow you on social media. Supports the following HTML tags: {}".format(
            ", ".join(settings.BLEACH_ALLOWED_TAGS)
        ),
        blank=True,
        strip_tags=True,
    )
    image = models.ImageField(
        verbose_name="Logo",
        upload_to="organizer",
        help_text="Preferably in landscape orientation or squared. Maximum size: 500KB. Supported formats: JPEG, PNG, WEBP.",
        blank=True,
        null=True,
        validators=[organizer_image_validator, validate_image_file_extension],
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    default_address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Main location",
        help_text="The location of your store or the location where most of your events take place.",
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
            self.filter(organizer__user=user, date__lte=end_date)
            .exclude(date__lt=start_date, edit_deadline_override__isnull=True)
            .exclude(category=Event.Category.OTHER)
            .annotate(result_cnt=Count("eventplayerresult"))
            .filter(result_cnt=0)
        )

        valid_event_ids = [event.id for event in initial_qs if event.can_be_edited()]
        return initial_qs.filter(id__in=valid_event_ids)


def tomorrow():
    return datetime.date.today() + datetime.timedelta(days=1)


class RecurringEvent(models.Model):
    """And event series that repeats on a regular basis. The events are scheduled from
    the start_date to the end_date based on the dates defined by its RecurrenceRules.
    """

    class Meta:
        verbose_name = "Event series"
        verbose_name_plural = "Event series"

    name = models.CharField(
        max_length=200,
        help_text="The name of this event series, e.g. 'Modern League Q1'",
    )
    start_date = models.DateField(
        default=tomorrow,
        help_text="The date of the first event of this event series. Can be in the past but only events without results will be rescheduled.",
    )
    end_date = models.DateField(
        help_text="The date of the last event of this event series. Can be up to 1 year in the future.",
    )

    def clean(self):
        super().clean()
        if self.end_date > datetime.date.today() + datetime.timedelta(days=365):
            raise ValidationError(
                {"end_date": "End date must be within 1 year from today."}
            )
        if self.start_date > self.end_date:
            raise ValidationError(
                {"start_date": "Start date must be before the end date."}
            )

        original_start_date = (
            RecurringEvent.objects.get(pk=self.pk).start_date if self.pk else None
        )
        # Allow leaving the start_date the same. Otherwise it can be maximum 1 year in the past.
        if (
            original_start_date != self.start_date
            and self.start_date < datetime.date.today() - datetime.timedelta(days=365)
        ):
            raise ValidationError(
                {
                    "start_date": "Start date can't be more than 1 year in the past, unless it stays the same."
                }
            )

    def __str__(self):
        return f"{self.name} from {self.start_date} to {self.end_date}"

    def get_delete_url(self):
        return reverse("recurring_event_delete", args=[self.pk])


class RecurrenceRule(models.Model):
    """Each RecurringEvent has multiple RecurrenceRules, which define the schedule of the event series.
    The weekday and week fields define which days of a month are affected by the rule.
    There are three types of rules:
    - Schedule: The event will be scheduled on the affected days.
    - Skip: The event will be skipped on these days (assuming it's scheduled by another rule).
    - SUL Regional: The event will be promoted to SUL Regional on these days.
    """

    class Weekday(models.TextChoices):
        MONDAY = "MONDAY", "Monday"
        TUESDAY = "TUESDAY", "Tuesday"
        WEDNESDAY = "WEDNESDAY", "Wednesday"
        THURSDAY = "THURSDAY", "Thursday"
        FRIDAY = "FRIDAY", "Friday"
        SATURDAY = "SATURDAY", "Saturday"
        SUNDAY = "SUNDAY", "Sunday"

    class Week(models.TextChoices):
        FIRST = "FIRST_WEEK", "First week of the month"
        SECOND = "SECOND_WEEK", "Second week of the month"
        SECOND_LAST = "SECOND_LAST_WEEK", "Second to last week of the month"
        LAST = "LAST_WEEK", "Last week of the month"
        EVERY = "EVERY_WEEK", "Every week"
        EVERY_OTHER = "EVERY_OTHER_WEEK", "Every other week"

    class Type(models.TextChoices):
        SCHEDULE = "SCHEDULE", "Scheduled"
        SKIP = "SKIP", "Skipped"
        REGIONAL = "REGIONAL", "Promoted to SUL Regional"

    recurring_event = models.ForeignKey(RecurringEvent, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        default=Type.SCHEDULE,
        help_text="Choose 'Scheduled' to run the event on each of those days. Choose 'Skipped' to skip the event on some days. Choose 'Promoted to SUL Regional' to make the event SUL Regional on these days.",
    )
    weekday = models.CharField(
        max_length=10,
        choices=Weekday.choices,
        default=Weekday.FRIDAY,
        help_text="The weekday your event will take place.",
    )
    week = models.CharField(
        max_length=20,
        choices=Week.choices,
        default=Week.EVERY,
        help_text="Which week of the month your event will take place.",
    )

    def __str__(self):
        return f"{self.get_type_display()} (every) {self.get_week_display()} on {self.get_weekday_display()}"


def event_image_validator(image):
    if image.size > 1.5 * 1024 * 1024:
        raise ValidationError("Image file too large ( > 1.5MB )")


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
    recurring_event = models.ForeignKey(
        RecurringEvent, on_delete=models.SET_NULL, null=True, blank=True
    )
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
    image = models.ImageField(
        upload_to="event",
        help_text="Preferably in landscape orientation. Maximum size: 1.5MB. Supported formats: JPEG, PNG, WEBP.",
        blank=True,
        null=True,
        validators=[event_image_validator, validate_image_file_extension],
    )
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Format(models.TextChoices):
        LIMITED = "LIMITED", "Limited"
        MODERN = "MODERN", "Modern"
        LEGACY = "LEGACY", "Legacy"
        PIONEER = "PIONEER", "Pioneer"
        STANDARD = "STANDARD", "Standard"
        EDH = "EDH", "Commander/EDH"
        DUEL_COMMANDER = "DC", "Duel Commander"
        PAUPER = "PAUPER", "Pauper"
        OLD_SCHOOL = "OS", "Old School"
        PRE_MODERN = "PM", "Premodern"
        VINTAGE = "VINTAGE", "Vintage"
        MULTIFORMAT = "MULTI", "Multi-Format"

    format = models.CharField(
        max_length=10,
        choices=Format.choices,
    )

    class Category(models.TextChoices):
        REGULAR = "REGULAR", "SUL Regular"
        REGIONAL = "REGIONAL", "SUL Regional"
        PREMIER = "PREMIER", "SUL Premier"
        OTHER = "OTHER", "Other"

    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        help_text="Select 'Other' for events without Swiss rounds and multiplayer events (including Two-Headed Giant).",
    )
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

    edit_deadline_override = models.DateField(
        help_text="A custom deadline for editing results, e.g. when a TO requested an extension to upload their results.",
        blank=True,
        null=True,
    )

    include_in_invoices = models.BooleanField(
        help_text="Whether this event will be in invoices.", default=True
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
        if self.category == Event.Category.OTHER:
            return ""
        return f"types/icons/{self.category.lower()}.png"

    def can_have_top8(self) -> bool:
        return self.category != Event.Category.REGULAR

    def can_be_edited(self) -> bool:
        """Returns whether changing the Event or its EventPlayerResults is allowed.

        A TO can edit the event when:
        -The event is not part of a season.
        -The event is recent (not older than settings.EVENT_MAX_AGE_FOR_RESULT_ENTRY)
        -The end of season deadline hasn't passed.
        -The deadline to edit the event was overridden by an admin.
        """
        today = datetime.date.today()
        if self.edit_deadline_override and today <= self.edit_deadline_override:
            return True

        season = find_season_by_date(self.date)
        if season is None:
            return True

        oldest_allowed = today - settings.EVENT_MAX_AGE_FOR_RESULT_ENTRY
        if self.date < oldest_allowed:
            return False

        return season.can_enter_results(today)

    @property
    def season(self) -> Season | None:
        return find_season_by_date(self.date)

    def can_be_deleted(self) -> bool:
        """Events can be deleted if they can still be edited or have no results."""
        return self.can_be_edited() or not self.eventplayerresult_set.exists()

    def copy_values_from(self, other: "Event", excluded_fields=None) -> "Event":
        """Copy values from another event into this one, retaining the excluded fields.
        Admin-related fields (results_validation_enabled, edit_deadline_override, include_in_invoices)
        and primary key (pk) are excluded by default.
        """
        default_excluded_fields = [
            "results_validation_enabled",
            "edit_deadline_override",
            "include_in_invoices",
            "id",
            "pk",
        ]

        for field in self._meta.fields:
            field_name = field.name

            if field_name not in default_excluded_fields + (excluded_fields or []):
                setattr(self, field_name, getattr(other, field_name))

        return self

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
        verbose_name = "Result"

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

    def get_delete_url(self):
        return reverse("single_result_delete", args=[self.pk])


class SpecialReward(models.Model):
    result = models.ForeignKey(EventPlayerResult, on_delete=models.CASCADE)
    byes = models.PositiveIntegerField(
        help_text="Number of additional byes the player receives for this result.",
        default=0,
    )
    direct_invite = models.BooleanField(
        help_text="Whether the player receives a direct invite for this result.",
        default=False,
    )


if "auditlog" in settings.INSTALLED_APPS:
    from auditlog.registry import auditlog

    auditlog.register(EventOrganizer)
    auditlog.register(Player, m2m_fields={"events"})
    auditlog.register(Event)
    auditlog.register(EventPlayerResult)
