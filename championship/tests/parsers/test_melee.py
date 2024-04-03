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

from championship.parsers import melee
from championship.parsers.parse_result import ParseResult

from .utils import load_test_html


class EventlinkStandingParser(TestCase):
    def setUp(self):
        self.text = load_test_html("melee_standings.csv")
        self.results = melee.parse_standings(self.text)

    def test_can_parse(self):
        want = [
            ParseResult("Antoine Renaud-Goud", 29, (9, 3, 2)),
            ParseResult("Jari Rentsch", 29, (9, 3, 2)),
            ParseResult("Christian Rothen", 28, (9, 4, 1)),
        ]
        l = len(want)
        self.assertEqual(want, self.results[:l])
