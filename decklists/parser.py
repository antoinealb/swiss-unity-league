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

from parsita import Failure, ParserContext, Success, lit, longest, reg, rep1, rep1sep
from parsita.util import constant


class DecklistParser(ParserContext, whitespace=r"[ \t]*"):  # type: ignore
    newline = longest(lit("\r\n"), lit("\n"), lit("\r"))
    integer = reg(r"[0-9]+") > int
    card = reg(r"[^\r\n]*")
    line = integer & card
    deck = rep1sep(line, newline)
