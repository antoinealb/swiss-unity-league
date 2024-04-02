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

from championship.parsers import mtgevent

from .utils import load_test_html


class MtgEventStandingsParser(TestCase):
    def setUp(self):
        self.text = load_test_html("mtgevent_ranking.html")
        self.results = mtgevent.parse_standings_page(self.text)

    def test_can_parse(self):
        want = [
            ("Toni Marty", 9, (3, 1, 0)),
            ("Eder Lars", 9, (3, 1, 0)),
            ("Pascal Merk", 9, (3, 1, 0)),
            ("Luca Riedmann", 9, (3, 1, 0)),
            ("Remus Kosmalla", 6, (2, 2, 0)),
        ]
        got = [(pr.name, pr.points, pr.record) for pr in self.results[:5]]
        self.assertEqual(want, got)
