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

from championship.parsers import eventlink

from .utils import load_test_html


class EventlinkStandingParser(TestCase):
    def setUp(self):
        self.text = load_test_html("eventlink_ranking.html")
        self.results = eventlink.parse_standings_page(self.text)

    def test_can_parse(self):
        want = [
            ("Jeremias Wildi", 10, (3, 0, 1)),
            ("Silvan Aeschbach", 9, (3, 1, 0)),
            ("Janosh Georg", 7, (2, 1, 1)),
        ]
        got = [(pr.name, pr.points, pr.record) for pr in self.results[:3]]
        self.assertEqual(want, got)
