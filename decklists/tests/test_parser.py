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

import os.path
from unittest import TestCase

from parameterized import parameterized
from parsita import Success

from decklists.parser import (
    AlternativeMana,
    Color,
    Colorless,
    DecklistParser,
    Hybrid,
    ManaParser,
    ParsedDecklistEntry,
    Phyrexian,
    Snow,
)


def read_decklist(name):
    path = os.path.join(os.path.dirname(__file__), name)
    with open(path) as f:
        return f.read()


class ParserTestCase(TestCase):
    def test_parse_integer(self):
        self.assertEqual(DecklistParser.integer.parse("42").unwrap(), 42)

    def test_parse_card(self):
        parsed = DecklistParser.card.parse("Thalia, Guardian of Thraben").unwrap()
        self.assertEqual("Thalia, Guardian of Thraben", parsed)

    def test_parse_combination(self):
        parsed = DecklistParser.line.parse("4 Thalia, Guardian of Thraben").unwrap()
        self.assertEqual([4, "Thalia, Guardian of Thraben"], parsed)

    def read_and_parse(self, name):
        decklist = read_decklist(name)
        res = DecklistParser.mtgo_deck.parse(decklist)
        self.assertIsInstance(res, Success)
        return res.unwrap()

    def test_parse_mtgo_format(self):
        got = self.read_and_parse("deck.txt")
        self.assertEqual(got.mainboard[0], ParsedDecklistEntry(4, "Unearth"))
        self.assertEqual(got.sideboard[0], ParsedDecklistEntry(2, "Toxic Deluge"))

    def test_parse_mtgo_format_no_sideboard_marker(self):
        got = self.read_and_parse("deck_no_sideboard_marker.txt")

        self.assertEqual(
            got.mainboard[0], ParsedDecklistEntry(4, "Anoint with Affliction")
        )
        self.assertEqual(got.sideboard[0], ParsedDecklistEntry(1, "Blot Out"))

    def test_parse_no_sideboard(self):
        res = DecklistParser.mtgo_deck.parse("4 Fry\n\n\n")
        self.assertIsInstance(res, Success)


class MwDeckTestCase(TestCase):
    """Test for Magic Workstation decks (.mwdeck, .dec)"""

    def test_parse_mwdeck_comment(self):
        got = DecklistParser.mwdeck_comment.parse("// Hello world")
        self.assertIsInstance(got, Success)

    @parameterized.expand(["MH2", "UL"])
    def test_parse_mwdeck_set(self, setcode):
        got = DecklistParser.mwdeck_set.parse(setcode)
        self.assertIsInstance(got, Success)

    @parameterized.expand(
        [
            ("2 [] Sink into Stupor", (False, 2, "Sink into Stupor")),
            ("3 [DIS] Spell Snare", (False, 3, "Spell Snare")),
            ("SB: 3 [DIS] Spell Snare", (True, 3, "Spell Snare")),
            ("// NAME : Dimir Control", "NAME : Dimir Control"),
        ]
    )
    def test_parse_mwdeck_line(self, line, want):
        got = DecklistParser.mwdeck_line.parse(line)
        self.assertIsInstance(got, Success)
        self.assertSequenceEqual(got.unwrap(), want)

    def test_parse_mwdeck_format(self):
        path = os.path.join(os.path.dirname(__file__), "deck.mwDeck")
        with open(path) as f:
            decklist = f.read()

        got = DecklistParser.mwdeck_deck.parse(decklist)
        self.assertIsInstance(got, Success)
        got = got.unwrap()
        self.assertEqual(got.mainboard[0], ParsedDecklistEntry(4, "Unearth"))
        self.assertEqual(got.sideboard[0], ParsedDecklistEntry(2, "Toxic Deluge"))


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

    def test_parse_hybrid_generic(self):
        """Parses hybrid generic / colored mana à la Spectral Procession."""
        # See Spectral Procession for an example card
        got = ManaParser.mana.parse("{2/W}").unwrap()
        want = [Hybrid((2, Color.WHITE))]
        self.assertEqual(want, got)

    def test_parse_split(self):
        """test parsing split cards mana"""
        # See Spectral Procession for an example card
        got = ManaParser.mana.parse("{2}{R} // {4}{W}").unwrap()
        want = AlternativeMana([[2, Color.RED], [4, Color.WHITE]])
        self.assertEqual(want, got)

    def test_parse_hybrid_colorless(self):
        """Parses hybrid colorless & colored mana (Ulalek, Fused Atrocity)."""
        got = ManaParser.mana.parse("{C/W}{C/U}{C/B}{C/R}{C/G}").unwrap()
        want = [
            Hybrid((Colorless, Color.WHITE)),
            Hybrid((Colorless, Color.BLUE)),
            Hybrid((Colorless, Color.BLACK)),
            Hybrid((Colorless, Color.RED)),
            Hybrid((Colorless, Color.GREEN)),
        ]
        self.assertEqual(want, got)
