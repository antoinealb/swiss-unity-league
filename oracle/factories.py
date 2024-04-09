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

import factory
from factory.django import DjangoModelFactory
from faker.providers import BaseProvider

import championship.factories  # noqa
from oracle.models import Card


class MagicProvider(BaseProvider):
    def card_name(self):
        return random.choice(
            [
                "Road of Return",
                "Storm Crow",
                "Snarlfang Vermin",
                "Walking Sponge",
                "Ravnica at War",
                "Greta, Sweettooth Scourge",
                "Torrent of Fire",
                "Wyluli Wolf",
            ]
        )

    def mana_cost(self):
        return random.choice(
            [
                "{3}",
                "{U}",
                "{G}{G}",
                "{1}{U}",
                "{B}",
                "{1}{U}",
                "{3}{W}",
                "{1}{B}{G}",
                "{3}{R}{R}",
                "{1}{G}",
            ]
        )


factory.Faker.add_provider(MagicProvider)


class CardFactory(DjangoModelFactory):
    class Meta:
        model = Card

    name = factory.Faker("card_name")
    mana_cost = factory.Faker("mana_cost")
    mana_value = factory.Faker("random_int", max=18)
    scryfall_uri = factory.Faker("uri")
