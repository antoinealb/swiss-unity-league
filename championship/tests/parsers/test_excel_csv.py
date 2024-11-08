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

from championship.parsers.excel_csv_parser import (
    MATCH_POINTS,
    PLAYER_NAME,
    RECORD,
    InvalidMatchPointsError,
    InvalidRecordError,
    PlayerNameNotFound,
    RecordOrMatchPointsNotFound,
    parse_standings_page,
)


class ExcelCsvStandingParser(TestCase):
    def test_can_parse_record(self):
        rows = [
            ["Player name", "Match points", "Record"],
            ["Jari Rentsch", "9", "3-1-0"],
            ["Noé Dumez", "8", "2-0-2"],
            ["RENAUD-GOUD, Antoine", "7", "2-1-1"],
        ]

        self.results = parse_standings_page(rows)
        want = [
            ("Jari Rentsch", 9, (3, 1, 0)),
            ("Noé Dumez", 8, (2, 0, 2)),
            ("RENAUD-GOUD, Antoine", 7, (2, 1, 1)),
        ]
        got = [(pr.name, pr.points, pr.record) for pr in self.results[:3]]
        self.assertEqual(want, got)

    def _create_rows(self, match_points):
        rows = []
        rows.append([PLAYER_NAME, MATCH_POINTS])  # Add header
        for i, points in enumerate(match_points, start=1):
            rows.append([f"Player {i}", str(points)])
        return rows

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
        wb = self._create_rows(match_points)
        self.results = parse_standings_page(wb)
        records = [pr.record for pr in self.results]
        self.assertEqual(want, records)


class ExcelCsvStandingParserExceptions(TestCase):

    def setUp(self):
        self.rows = [
            [PLAYER_NAME, MATCH_POINTS, RECORD],
            ["Jari Rentsch", "9", "3-1-0"],
            ["Noé Dumez", "8", "2-0-2"],
            ["RENAUD-GOUD, Antoine", "7", "2-1-1"],
        ]

    def delete_column(self, column_name):
        index = self.rows[0].index(column_name)
        for row in self.rows:
            del row[index]

    def test_player_name_not_found(self):
        self.delete_column(PLAYER_NAME)
        with self.assertRaises(PlayerNameNotFound):
            parse_standings_page(self.rows)

    def test_record_or_match_points_not_found(self):
        self.delete_column(MATCH_POINTS)
        self.delete_column(RECORD)
        with self.assertRaises(RecordOrMatchPointsNotFound):
            parse_standings_page(self.rows)

    def test_invalid_record(self):
        self.rows[1][2] = "invalid"
        with self.assertRaises(InvalidRecordError):
            parse_standings_page(self.rows)

    def test_invalid_match_points(self):
        self.rows[1][1] = "invalid"
        self.delete_column(RECORD)
        with self.assertRaises(InvalidMatchPointsError):
            parse_standings_page(self.rows)
