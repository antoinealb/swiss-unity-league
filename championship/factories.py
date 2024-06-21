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

from .models import *
from .season import SEASON_2023, SEASON_2024


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

        if extracted == None:
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


class Event2024Factory(EventFactory):
    date = factory.Faker(
        "date_between",
        start_date=SEASON_2024.start_date,
        end_date=SEASON_2024.end_date,
    )
    category = factory.Faker(
        "random_element",
        elements=RANKED_EVENT_CATEGORIES,
    )


class RankedEventFactory(EventFactory):
    category = factory.Faker(
        "random_element",
        elements=RANKED_EVENT_CATEGORIES,
    )


class EventPlayerResultFactory(DjangoModelFactory):
    class Meta:
        model = EventPlayerResult

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

    result = factory.SubFactory(EventPlayerResultFactory)


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
