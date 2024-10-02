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

CARD_NAMES = [
    "Road of Return",
    "Storm Crow",
    "Snarlfang Vermin",
    "Walking Sponge",
    "Ravnica at War",
    "Greta, Sweettooth Scourge",
    "Torrent of Fire",
    "Wyluli Wolf",
    "Static Orb",
    "Sensory Deprivation",
    "Road of Return",
    "Storm Crow",
    "Snarlfang Vermin",
    "Walking Sponge",
    "Ravnica at War",
    "Greta, Sweettooth Scourge",
    "Torrent of Fire",
    "Wyluli Wolf",
    "Pteramander",
    "Nantuko Elder",
    "Vedalken Heretic",
    "Waterknot",
    "Ruthless Knave",
    "Palinchron",
    "Hua Tuo, Honored Physician",
    "Veil of Summer",
    "Disposal Mummy",
    "Wei Strike Force",
    "Marang River Prowler",
    "Aura Graft",
    "Murk Dwellers",
    "Whispering Shade",
    "Saheeli's Artistry",
    "Kalitas, Bloodchief of Ghet",
    "Safewright Quest",
    "Instill Infection",
    "Weakstone",
    "Strength of Night",
    "High-Rise Sawjack",
    "Keldon Raider",
    "Leopard-Spotted Jiao",
    "Escape Tunnel",
    "Food Fight",
    "Behemoth Sledge",
    "Toluz, Clever Conductor",
    "Kindred Discovery",
    "Stern Marshal",
    "Trapjaw Tyrant",
]


class MagicProvider(BaseProvider):
    card_name_index = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cards = list(CARD_NAMES)
        random.shuffle(self.cards)

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

    def card_type(self):
        return random.choice(
            [
                "Land",
                "Creature",
                "Artifact",
                "Enchantment",
                "Planeswalker",
                "Battle",
                "Instant",
                "Sorcery",
            ]
        )

    def card_name(self) -> str:
        """Provide a unique magic card name.

        To provide "unique-in-a-single-test" card names, we go through a
        sequence of card names, eventually looping around. This guarantees
        unicity in a given unit test, as long as CardFactory is called less
        than len(CARD_NAMES) times in a single test.
        """
        self.card_name_index += 1
        if self.card_name_index >= len(self.cards):
            self.card_name_index = 0

        return self.cards[self.card_name_index]


factory.Faker.add_provider(MagicProvider)


class CardFactory(DjangoModelFactory):
    class Meta:
        model = Card

    name = factory.Faker("card_name")
    mana_cost = factory.Faker("mana_cost")
    mana_value = factory.Faker("random_int", max=18)
    type_line = factory.Faker("card_type")
    scryfall_uri = factory.Faker("uri")
    image_uri = factory.Faker("uri")
