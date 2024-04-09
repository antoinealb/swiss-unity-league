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

from decklists.parser import (
    Color,
    Colorless,
    DecklistParser,
    Hybrid,
    ManaParser,
    Phyrexian,
    Snow,
)


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


class ManaParserTestCase(TestCase):
    def test_parse_generic_mana(self):
        a = ManaParser.mana.parse("{3}").unwrap()
        self.assertEqual([3], a)

    def test_parse_x(self):
        a = ManaParser.mana.parse("{X}").unwrap()
        self.assertEqual(["X"], a)

    def test_parse_colored(self):
        a = ManaParser.color.parse("G").unwrap()
        self.assertIsInstance(a, Color)
        self.assertEqual(Color.GREEN, a)

    def test_parse_hybrid(self):
        a = ManaParser.hybrid.parse("G/U").unwrap()
        self.assertIsInstance(a, Hybrid)
        self.assertEqual((Color.GREEN, Color.BLUE), a.colors)

    def test_parse_phyrexian(self):
        a = ManaParser.phyrexian.parse("B/P").unwrap()
        self.assertIsInstance(a, Phyrexian)
        self.assertEqual(Color.BLACK, a.color)

    def test_parse_phyrexian_hybrid(self):
        got = ManaParser.phyrexian.parse("G/U/P").unwrap()
        want = Phyrexian(Hybrid((Color.GREEN, Color.BLUE)))
        self.assertEqual(want, got)

    def test_parse_tamyo_compleated_sage(self):
        got = ManaParser.mana.parse("{2}{G}{G/U/P}{U}").unwrap()
        want = [
            2,
            Color.GREEN,
            Phyrexian(Hybrid((Color.GREEN, Color.BLUE))),
            Color.BLUE,
        ]
        self.assertEqual(got, want)

    def test_parse_snow(self):
        got = ManaParser.mana_inside.parse("S").unwrap()
        want = Snow
        self.assertEqual(want, got)

    def test_parse_colorless(self):
        got = ManaParser.mana_inside.parse("C").unwrap()
        want = Colorless
        self.assertEqual(want, got)

    def test_parse_hybrid(self):
        """Parses hybrid generic / colored mana à la Spectral Procession."""
        # See Spectral Procession for an example card
        got = ManaParser.mana.parse("{2/W}").unwrap()
        want = [Hybrid((2, Color.WHITE))]
        self.assertEqual(want, got)
