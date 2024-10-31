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

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User

import factory
from factory.django import DjangoModelFactory
from faker.providers import BaseProvider

from .models import (
    Address,
    Event,
    EventOrganizer,
    OrganizerLeague,
    Player,
    RecurrenceRule,
    RecurringEvent,
    Result,
    SpecialReward,
)
from .season import SEASON_2023, SEASON_2024, SEASON_2025


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
        elements=Address.Country.values,
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
    def addresses(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted is None:
            # Create 3 new random addresses.
            addresses = AddressFactory.create_batch(3, organizer=self)
            for address in addresses:
                self.addresses.add(address)

            # Set one as the default
            self.default_address = addresses[0]
            self.save()


class PlayerFactory(DjangoModelFactory):
    class Meta:
        model = Player

    name = factory.Faker("name", locale="fr_CH")


RANKED_EVENT_CATEGORIES = [
    Event.Category.PREMIER,
    Event.Category.REGIONAL,
    Event.Category.REGULAR,
]


class EventFactory(DjangoModelFactory):
    class Meta:
        model = Event

    name = factory.Faker("mtg_event_name")
    organizer = factory.SubFactory(EventOrganizerFactory)
    date = factory.Faker(
        "date_between",
        start_date=SEASON_2023.start_date,
        end_date=SEASON_2023.end_date,
    )
    url = factory.Faker("uri")

    format = factory.Faker(
        "random_element",
        elements=Event.Format.values,
    )

    category = factory.Faker(
        "random_element",
        elements=Event.Category.values,
    )


class RankedEventFactory(EventFactory):
    category = factory.Faker(
        "random_element",
        elements=Event.Category.ranked_values(),
    )

    @factory.post_generation
    def players(self, create, players, **kwargs):
        if not create or players is None:
            return

        if isinstance(players, int):
            players = PlayerFactory.create_batch(players)

        num_players = len(players)
        for i, player in enumerate(players):
            rank = i + 1

            ResultFactory(
                player=player,
                points=num_players - i,
                ranking=rank,
                event=self,
            )
        return self

    @factory.post_generation
    def with_tops(self, create, with_tops, **kwargs):
        if not create or with_tops is None:
            return

        if with_tops not in [4, 8]:
            raise ValueError("with_tops must be 4 or 8")

        if self.result_set.count() < with_tops:
            raise ValueError(f"Not enough players to have a top {with_tops}")

        results = self.result_set.order_by("ranking").all()
        for rank in range(1, with_tops + 1):
            if rank == 1:
                ser = Result.SingleEliminationResult.WINNER
            elif rank == 2:
                ser = Result.SingleEliminationResult.FINALIST
            elif rank <= 4:
                ser = Result.SingleEliminationResult.SEMI_FINALIST
            elif rank <= 8:
                ser = Result.SingleEliminationResult.QUARTER_FINALIST
            else:
                ser = None
            result = results[rank - 1]
            result.single_elimination_result = ser
            result.save()
        return self


class Event2024Factory(RankedEventFactory):
    date = factory.Faker(
        "date_between",
        start_date=SEASON_2024.start_date,
        end_date=SEASON_2024.end_date,
    )


class Event2025Factory(RankedEventFactory):
    date = factory.Faker(
        "date_between",
        start_date=SEASON_2025.start_date,
        end_date=SEASON_2025.end_date,
    )


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
        elements=Event.Category.ranked_values(),
    )

    playoffs = factory.Faker("boolean")
