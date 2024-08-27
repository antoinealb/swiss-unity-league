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

from parameterized import parameterized

from championship.parsers import spicerack

from .utils import load_test_html


class SpicerackStandingsParser(TestCase):

    def test_get_rounds(self):
        self.text = load_test_html("spicerack/get_all_rounds.json")
        round = spicerack.parse_rounds_json(self.text)
        self.assertEqual(round["id"], 691)
        self.assertEqual(round["round_number"], 5)

    def test_parse_standings(self):
        self.text = load_test_html("spicerack/include_all_standings.json")
        total_rounds = 5
        self.results = spicerack.parse_standings_json(self.text, total_rounds)
        want_standings = [
            ("Filipe Sousa", 11, (3, 0, 2), None),
            (
                "Eloi Benvenuti",
                11,
                (3, 0, 2),
                None,
            ),
            (
                "Xavier Boraley",
                10,
                (3, 1, 1),
                None,
            ),
        ]
        got_result = [
            (pr.name, pr.points, pr.record, pr.decklist_url) for pr in self.results[:3]
        ]
        self.assertEqual(want_standings, got_result)

    @parameterized.expand(
        [
            "https://www.spicerack.gg/admin/events/1182690#setup",
            "https://www.spicerack.gg/admin/events/1182690#tournament",
            "https://www.spicerack.gg/events/1182690",
            "https://www.spicerack.gg/events/1182690/tournament",
        ]
    )
    def test_extract_event_id_from_url(self, url):
        self.assertEqual(spicerack.extract_event_id_from_url(url), "1182690", url)
