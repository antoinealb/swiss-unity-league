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

import pandas as pd
from parameterized import parameterized

from championship.parsers.excel_csv_parser import *


class ExcelCsvStandingParser(TestCase):
    def test_can_parse_record(self):
        self.df = pd.read_excel("championship/tests/parsers/excel_ranking.xlsx")
        self.results = parse_standings_page(self.df)
        want = [
            ("Jari Rentsch", 9, (3, 1, 0)),
            ("Noé Dumez", 8, (2, 0, 2)),
            ("RENAUD-GOUD, Antoine", 7, (2, 1, 1)),
        ]
        got = [(pr.name, pr.points, pr.record) for pr in self.results[:3]]
        self.assertEqual(want, got)

    def _create_df(self, match_points):
        self.df = pd.DataFrame(
            {
                PLAYER_NAME: [f"Player {i}" for i in range(1, len(match_points) + 1)],
                MATCH_POINTS: [str(s) for s in match_points],
            }
        )

    @parameterized.expand(
        [
            (
                [9, 9, 9, 9, 7, 7, 6, 6, 3, 3, 3],
                [
                    (3, 1, 0),
                    (3, 1, 0),
                    (3, 1, 0),
                    (3, 1, 0),
                    (2, 1, 1),
                    (2, 1, 1),
                    (2, 2, 0),
                    (2, 2, 0),
                    (1, 3, 0),
                    (1, 3, 0),
                    (1, 3, 0),
                ],
            ),
            (
                [10, 9, 9, 7, 7, 7, 6, 6, 3, 3, 3],
                [
                    (3, 0, 1),
                    (3, 1, 0),
                    (3, 1, 0),
                    (2, 1, 1),
                    (2, 1, 1),
                    (2, 1, 1),
                    (2, 2, 0),
                    (2, 2, 0),
                    (1, 3, 0),
                    (1, 3, 0),
                    (1, 3, 0),
                ],
            ),
        ]
    )
    def test_can_parse_match_points(self, match_points, want):
        self._create_df(match_points)
        self.results = parse_standings_page(self.df)
        records = [pr.record for pr in self.results]
        self.assertEqual(want, records)


class ExcelCsvStandingParserExceptions(TestCase):
    def setUp(self):
        self.df = pd.read_excel("championship/tests/parsers/excel_ranking.xlsx")

    def test_player_name_not_found(self):
        del self.df[PLAYER_NAME]
        with self.assertRaises(PlayerNameNotFound):
            parse_standings_page(self.df)

    def test_record_or_match_points_not_found(self):
        del self.df[RECORD]
        del self.df[MATCH_POINTS]
        with self.assertRaises(RecordOrMatchPointsNotFound):
            parse_standings_page(self.df)

    def test_invalid_record(self):
        self.df.loc[0, RECORD] = "invalid"
        with self.assertRaises(InvalidRecordError):
            parse_standings_page(self.df)

    def test_invalid_match_points(self):
        del self.df[RECORD]
        self.df[MATCH_POINTS] = self.df[MATCH_POINTS].astype(str)
        self.df.loc[0, MATCH_POINTS] = "invalid"
        with self.assertRaises(InvalidMatchPointsError):
            parse_standings_page(self.df)
