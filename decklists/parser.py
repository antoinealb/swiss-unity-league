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

import dataclasses
import enum

from parsita import (
    ParserContext,
    Success,
    eof,
    failure,
    lit,
    longest,
    opt,
    reg,
    rep,
    rep1,
    rep1sep,
    repsep,
    success,
    until,
)
from parsita.util import constant


@dataclasses.dataclass
class ParsedDecklistEntry:
    qty: int
    name: str


@dataclasses.dataclass
class ParsedDecklist:
    mainboard: list
    sideboard: list


def non_null_length(*args):
    if not args or args[0] == "":
        return failure("Should not be null length")
    return success(args[0])


def _convert_mtgo_parse_result(result):
    main = [ParsedDecklistEntry(r[0], r[1]) for r in result[0]]
    side = [ParsedDecklistEntry(r[0], r[1]) for r in result[1]]
    return ParsedDecklist(mainboard=main, sideboard=side)


def _convert_mwdeck_result(result):
    # Discard comments
    result = [r for r in result if isinstance(r, list)]
    main = [ParsedDecklistEntry(r[1], r[2]) for r in result if not r[0]]
    side = [ParsedDecklistEntry(r[1], r[2]) for r in result if r[0]]
    return ParsedDecklist(mainboard=main, sideboard=side)


class DecklistParser(ParserContext, whitespace=r"[ \t]*"):  # type: ignore
    # Generic utility functions
    newline = longest(lit("\r\n"), lit("\n"), lit("\r"))
    until_end_of_line = until(newline | eof) >= non_null_length
    integer = reg(r"[0-9]+") > int
    card = until_end_of_line > (lambda s: s.rstrip())

    # Magic Workstation (mwdeck) format
    mwdeck_set = reg(r"[0-9A-Z]+")
    mwdeck_sideboard = lit("SB:")
    mwdeck_card = (
        (opt(mwdeck_sideboard) > (lambda s: bool(s)))
        & (integer << lit("[") << opt(mwdeck_set) << lit("]"))
        & card
    )
    mwdeck_comment = lit("//") >> until_end_of_line
    mwdeck_line = mwdeck_card | mwdeck_comment
    mwdeck_deck = (
        repsep(mwdeck_line, newline) << opt(newline)
    ) > _convert_mwdeck_result

    # MTGO / txt format
    line = integer & card
    mtgo_sideboard = rep(newline) & opt(lit("Sideboard") & newline)
    mtgo_part = repsep(line, newline) << (newline | eof)
    mtgo_deck = (
        rep(newline) >> ((mtgo_part << mtgo_sideboard) & mtgo_part)
        > _convert_mtgo_parse_result
    )

    # Put together
    deck = mwdeck_deck | mtgo_deck


class Color(enum.Enum):
    WHITE = "W"
    BLUE = "U"
    RED = "R"
    BLACK = "B"
    GREEN = "G"


@dataclasses.dataclass
class Hybrid:
    colors: tuple[Color | int, Color]


@dataclasses.dataclass
class Phyrexian:
    color: Color


@dataclasses.dataclass
class AlternativeMana:
    content: list


Snow = object()
Colorless = object()


class ManaParser(ParserContext):
    integer = reg(r"[0-9]+") > int
    color = longest(*(lit(s) for s in "WURBG")) > Color
    colorless = lit("C") > constant(Colorless)
    letter = lit("X") | lit("Y") | lit("Z")
    hybrid = ((color | integer | colorless) << "/" & color) > (
        lambda s: Hybrid(tuple(s))
    )
    phyrexian = (color | hybrid) << lit("/P") > Phyrexian
    snow = lit("S") > constant(Snow)
    mana_inside = integer | color | letter | hybrid | phyrexian | snow | colorless
    mana_with_braces = rep1("{" >> mana_inside << "}")
    mana = mana_with_braces | (rep1sep(mana_with_braces, " // ") > AlternativeMana)


def parse_mana(mana_cost: str):
    res = ManaParser.mana.parse(mana_cost)
    if isinstance(res, Success):
        return res.unwrap()
    raise ValueError(res.failure())
