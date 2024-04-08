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

from unittest import TestCase

from decklists.parser import DecklistParser


class ParserTestCase(TestCase):
    def test_parse_integer(self):
        self.assertEqual(DecklistParser.integer.parse("42").unwrap(), 42)

    def test_parse_card(self):
        parsed = DecklistParser.card.parse("Thalia, Guardian of Thraben").unwrap()
        self.assertEqual("Thalia, Guardian of Thraben", parsed)

    def test_parse_combination(self):
        parsed = DecklistParser.line.parse("4 Thalia, Guardian of Thraben").unwrap()
        self.assertEqual([4, "Thalia, Guardian of Thraben"], parsed)

    def test_parse_deck(self):
        decklist = """4 Thalia, Guardian of Thraben
        4 Lightning Bolt"""
        want = [[4, "Thalia, Guardian of Thraben"], [4, "Lightning Bolt"]]
        got = DecklistParser.deck.parse(decklist).unwrap()
        self.assertEqual(want, got)

    def test_parse_deck_with_windows_newsline(self):
        decklist = "4 Thalia, Guardian of Thraben\r\n4 Lightning Bolt"
        want = [[4, "Thalia, Guardian of Thraben"], [4, "Lightning Bolt"]]
        got = DecklistParser.deck.parse(decklist).unwrap()
        self.assertEqual(want, got)
