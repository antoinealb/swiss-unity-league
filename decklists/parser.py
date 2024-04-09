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
    Failure,
    ParserContext,
    Success,
    lit,
    longest,
    reg,
    rep1,
    rep1sep,
    repsep,
)
from parsita.util import constant


class DecklistParser(ParserContext, whitespace=r"[ \t]*"):  # type: ignore
    newline = longest(lit("\r\n"), lit("\n"), lit("\r"))
    integer = reg(r"[0-9]+") > int
    card = reg(r"[^\r\n]*")
    line = integer & card
    deck = repsep(line, newline)


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
    letter = lit("X") | lit("Y") | lit("Z")
    hybrid = ((color | integer) << "/" & color) > (lambda s: Hybrid(tuple(s)))
    phyrexian = (color | hybrid) << lit("/P") > Phyrexian
    snow = lit("S") > constant(Snow)
    colorless = lit("C") > constant(Colorless)
    mana_inside = integer | color | letter | hybrid | phyrexian | snow | colorless
    mana_with_braces = rep1("{" >> mana_inside << "}")
    mana = mana_with_braces | (rep1sep(mana_with_braces, " // ") > AlternativeMana)


def parse_mana(mana_cost: str):
    res = ManaParser.mana.parse(mana_cost)
    if isinstance(res, Success):
        return res.unwrap()
    raise ValueError(res.failure())
