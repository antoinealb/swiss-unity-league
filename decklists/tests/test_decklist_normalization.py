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

from dataclasses import dataclass
from typing import Iterable, TypeAlias

from django.test import TestCase

from decklists.views import DecklistEntry, annotate_card_attributes, normalize_decklist
from oracle.factories import CardFactory
from oracle.models import Card


class ListProcessing(TestCase):
    databases = ["oracle"]

    def test_normalize_cards_quantity(self):
        decklist = [
            DecklistEntry(2, "Fog"),
            DecklistEntry(4, "Fly"),
            DecklistEntry(2, "Fog"),
        ]
        want = [DecklistEntry(4, "Fog"), DecklistEntry(4, "Fly")]
        got, _ = normalize_decklist(decklist)
        self.assertEqual(want, got)

    def test_annotate_cards(self):
        c = CardFactory()
        decklist = [DecklistEntry(4, c.name)]
        want = [
            DecklistEntry(
                4,
                c.name,
                mana_cost=c.mana_cost,
                mana_value=c.mana_value,
                scryfall_uri=c.scryfall_uri,
            )
        ]
        got, _ = annotate_card_attributes(decklist)
        self.assertEqual(want, got)

    def test_annotate_missing_card(self):
        decklist = [DecklistEntry(4, "Foobar")]
        want_errors = ["Unknown card 'Foobar'"]
        got, errors = annotate_card_attributes(decklist)
        self.assertEqual(got, decklist)
        self.assertEqual(want_errors, errors)
