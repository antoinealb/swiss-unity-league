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

import random
from typing import Iterable

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User

import factory
from django_countries import countries
from factory.django import DjangoModelFactory
from faker.providers import BaseProvider

from .models import (
    Address,
    Event,
    EventOrganizer,
    NationalLeaderboard,
    OrganizerLeague,
    Player,
    PlayerProfile,
    PlayerSeasonData,
    RecurrenceRule,
    RecurringEvent,
    Result,
    SpecialReward,
)
from .seasons.definitions import SEASON_2023, SEASON_2024, SEASON_2025


class MagicProvider(BaseProvider):
    def mtg_event_name(self):
        f = random.choice(["Modern", "Legacy", "Standard"])
        t = random.choice(["1k", "2k", "Open", "RCQ"])
        return f"{f} {t}"


factory.Faker.add_provider(MagicProvider)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("email")
    password = factory.LazyFunction(lambda: make_password("foobar"))


class AddressFactory(DjangoModelFactory):
    class Meta:
        model = Address

    location_name = factory.Faker("company", locale="fr_CH")
    street_address = factory.Faker("street_address", locale="fr_CH")
    city = factory.Faker("city", locale="fr_CH")
    postal_code = factory.Faker("postcode", locale="fr_CH")
    region = factory.Faker(
        "random_element",
        elements=Address.Region.values,
    )
    country = factory.Faker(
        "random_element",
        elements=countries.countries.keys(),
    )


class EventOrganizerFactory(DjangoModelFactory):
    class Meta:
        model = EventOrganizer

    name = factory.Faker("company", locale="fr_CH")
    contact = factory.Faker("email")
    description = factory.Faker("text")
    user = factory.SubFactory(UserFactory)
    url = factory.Faker("uri")

    @factory.post_generation
    def default_address(self, create, extracted, **kwargs):
        if not create:
            return
        self.default_address = AddressFactory(organizer=self)
        self.save()


class PlayerFactory(DjangoModelFactory):
    class Meta:
        model = Player

    name = factory.Faker("name", locale="fr_CH")


class PlayerProfileFactory(DjangoModelFactory):
    class Meta:
        model = PlayerProfile

    player = factory.SubFactory(PlayerFactory)
    status = PlayerProfile.Status.APPROVED
    consent_for_website = True
    pronouns = factory.Faker(
        "random_element",
        elements=PlayerProfile.Pronouns.values,
    )
    custom_pronouns = factory.Faker("text", max_nb_chars=20)
    date_of_birth = factory.Faker("date_of_birth")
    hometown = factory.Faker("city", locale="fr_CH")
    bio = factory.Faker("paragraph", nb_sentences=3)
    image = factory.Faker("image_url")


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    class Params:
        season = SEASON_2023
        excluded_categories: list[Event.Category] = []

    name = factory.Faker("mtg_event_name")
    organizer = factory.SubFactory(EventOrganizerFactory)
    url = factory.Faker("uri")

    format = factory.Faker(
        "random_element",
        elements=Event.Format.values,
    )

    category = factory.LazyAttribute(
        lambda obj: random.choice(
            [c for c in Event.Category.values if c not in obj.excluded_categories]
        )
    )

    date = factory.LazyAttribute(
        lambda obj: factory.Faker._get_faker().date_between(
            start_date=obj.season.start_date,
            end_date=obj.season.end_date,
        )
    )


class RankedEventFactory(EventFactory):
    """
    Factory to create Event instances with players and results.

    Special attributes:
        players (Iterable[Player] | int): Players list or number of players to create.
        players__country (str): Optional; Specify the country code for the PlayerSeasonData.
        with_tops (int): Optional; Specify 4 or 8 to assign playoff results to the top players.

    Usage:
        ranked_event = RankedEventFactory(players=10, players__country="IT", with_tops=4)
    """

    class Params:
        excluded_categories = [Event.Category.OTHER]

    @factory.post_generation
    def players(self, create: bool, players: Iterable[Player] | int, **kwargs):

        if not create or not players:
            return

        if isinstance(players, int):
            players = PlayerFactory.create_batch(players)

        num_players = len(players)  # type: ignore
        for i, player in enumerate(players):  # type: ignore
            rank = i + 1

            ResultFactory(
                player=player,
                points=num_players - i,
                ranking=rank,
                event=self,
                player_country=kwargs.get("country"),
            )
        return self

    @factory.post_generation
    def with_tops(self, create: bool, with_tops: int, **kwargs):
        if not create or with_tops is None:
            return

        if with_tops not in [4, 8]:
            raise ValueError("with_tops must be 4 or 8")

        if self.result_set.count() < with_tops:
            raise ValueError(f"Not enough players to have a top {with_tops}")

        results = self.result_set.order_by("ranking").all()
        for rank in range(1, with_tops + 1):
            if rank == 1:
                playoff_result = Result.PlayoffResult.WINNER
            elif rank == 2:
                playoff_result = Result.PlayoffResult.FINALIST
            elif rank <= 4:
                playoff_result = Result.PlayoffResult.SEMI_FINALIST
            elif rank <= 8:
                playoff_result = Result.PlayoffResult.QUARTER_FINALIST
            else:
                playoff_result = None
            result = results[rank - 1]
            result.playoff_result = playoff_result
            result.save()
        return self


class OldCategoryRankedEventFactory(RankedEventFactory):
    category = factory.Faker(
        "random_element",
        elements=[
            c.name  # type: ignore
            for c in [
                Event.Category.REGULAR,
                Event.Category.REGIONAL,
                Event.Category.PREMIER,
            ]
        ],
    )


class Event2024Factory(OldCategoryRankedEventFactory):
    class Params:
        season = SEASON_2024


class Event2025Factory(OldCategoryRankedEventFactory):
    class Params:
        season = SEASON_2025


class ResultFactory(DjangoModelFactory):
    class Meta:
        model = Result

    event = factory.SubFactory(RankedEventFactory)
    player = factory.SubFactory(PlayerFactory)
    points = factory.LazyAttribute(lambda o: 3 * o.win_count + o.draw_count)
    ranking = factory.Faker("random_int", min=1, max=30)
    win_count = factory.Faker("random_int", min=0, max=3)
    loss_count = factory.Faker("random_int", min=0, max=3)
    draw_count = factory.Faker("random_int", min=0, max=3)

    @factory.post_generation
    def player_country(self, create, country, **kwargs):
        if create and country:
            PlayerSeasonData.objects.create(
                player=self.player,
                season_slug=self.event.season.slug,
                country=country,
            )


class SpecialRewardFactory(DjangoModelFactory):
    class Meta:
        model = SpecialReward

    result = factory.SubFactory(ResultFactory)


class RecurringEventFactory(DjangoModelFactory):
    class Meta:
        model = RecurringEvent

    name = factory.Faker("mtg_event_name")
    end_date = factory.Faker(
        "date_between", start_date=SEASON_2023.start_date, end_date=SEASON_2023.end_date
    )


class RecurrenceRuleFactory(DjangoModelFactory):
    class Meta:
        model = RecurrenceRule

    weekday = factory.Faker(
        "random_element",
        elements=RecurrenceRule.Weekday.values,
    )

    week = factory.Faker(
        "random_element",
        elements=RecurrenceRule.Week.values,
    )

    type = factory.Faker(
        "random_element",
        elements=RecurrenceRule.Type.values,
    )

    recurring_event = factory.SubFactory(RecurringEventFactory)


class OrganizerLeagueFactory(DjangoModelFactory):
    class Meta:
        model = OrganizerLeague

    name = factory.Faker("mtg_event_name")
    organizer = factory.SubFactory(EventOrganizerFactory)
    start_date = SEASON_2023.start_date
    end_date = SEASON_2023.end_date

    format = factory.Faker(
        "random_element",
        elements=Event.Format.values,
    )

    category = factory.Faker(
        "random_element",
        elements=[
            c.name  # type: ignore
            for c in [
                Event.Category.REGULAR,
                Event.Category.REGIONAL,
                Event.Category.PREMIER,
            ]
        ],
    )

    playoffs = factory.Faker("boolean")


class NationalLeaderboardFactory(DjangoModelFactory):
    class Meta:
        model = NationalLeaderboard

    country = factory.Faker(
        "random_element",
        elements=countries.countries.keys(),
    )
