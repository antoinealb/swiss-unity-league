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
import random

from django.utils import timezone

import factory
from factory.django import DjangoModelFactory
from faker.providers import BaseProvider

import championship.factories
import decklists.models


class MagicProvider(BaseProvider):
    def deck_archetype(self):
        return random.choice(
            [
                "Cascade Crash",
                "4/5c Aggro",
                "UR Aggro",
                "Rakdos Aggro",
                "Hardened Scales",
                "Merfolk",
                "The Underworld Cookbook",
                "Red Deck Wins",
                "Jund",
                "Mono Black Aggro",
                "Martyr Life",
                "Temur Aggro",
                "Elementals",
                "The Rock",
                "Boros Aggro",
                "Gruul Aggro",
                "Orzhov Midrange",
            ]
        )


factory.Faker.add_provider(MagicProvider)


def _publication_time(o):
    now = timezone.now()
    dt = datetime.timedelta(hours=1)
    if o.published:
        return now - dt
    else:
        return now + dt


class CollectionFactory(DjangoModelFactory):
    class Meta:
        model = decklists.models.Collection

    class Params:
        published = False

    # By default the publication time is when the decklists are published
    submission_deadline = factory.LazyAttribute(lambda o: o.publication_time)
    publication_time = factory.LazyAttribute(_publication_time)

    event = factory.SubFactory(championship.factories.EventFactory)


class DecklistFactory(DjangoModelFactory):
    class Meta:
        model = decklists.models.Decklist

    collection = factory.SubFactory(CollectionFactory)
    player = factory.SubFactory(championship.factories.PlayerFactory)
    archetype = factory.Faker("deck_archetype")
