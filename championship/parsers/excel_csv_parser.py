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

from championship.parsers.general_parser_functions import (
    estimate_rounds,
    parse_record,
    record_to_points,
)
from championship.parsers.parse_result import ParseResult

PLAYER_NAME = "PLAYER_NAME"
RECORD = "RECORD"
MATCH_POINTS = "MATCH_POINTS"


def _standings(data):
    header = data[0]
    header = [col.strip().upper().replace(" ", "_") for col in header]
    defined_cols = [col for col in [PLAYER_NAME, RECORD, MATCH_POINTS] if col in header]

    if PLAYER_NAME not in defined_cols:
        raise PlayerNameNotFound()

    player_name_index = header.index(PLAYER_NAME)
    record_index = header.index(RECORD) if RECORD in header else None
    match_points_index = header.index(MATCH_POINTS) if MATCH_POINTS in header else None

    if record_index is not None:
        for row in data[1:]:
            if not row[player_name_index]:
                continue

            name = row[player_name_index]
            record_string = row[record_index]
            try:
                parsed_record = parse_record(record_string)
                points = record_to_points(record_string)
            except ValueError:
                raise InvalidRecordError(name, record_string)

            yield ParseResult(name=name, points=points, record=parsed_record)

    elif match_points_index is not None:
        name_points_list = []
        for row in data[1:]:
            if not row[player_name_index]:
                continue

            name = row[player_name_index]
            try:
                points = int(row[match_points_index])
                name_points_list.append((name, points))
            except Exception:
                raise InvalidMatchPointsError(name, row[match_points_index])

        match_points_list = [points for _, points in name_points_list]
        num_rounds = estimate_rounds(match_points_list)

        for name, points in name_points_list:
            wins = points // 3
            draws = points % 3
            losses = num_rounds - wins - draws
            yield ParseResult(name=name, points=points, record=(wins, losses, draws))

    else:
        raise RecordOrMatchPointsNotFound()


def parse_standings_page(data):
    return list(_standings(data))


class PlayerNameNotFound(ValueError):
    def __init__(self, message=f"Column {PLAYER_NAME} not found", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

    ui_error_message = f"The column {PLAYER_NAME} was not found in the excel file. Please rename the column that contains the first and lastname of the player to {PLAYER_NAME}."


class RecordOrMatchPointsNotFound(ValueError):
    def __init__(
        self, message=f"Column {RECORD} or {MATCH_POINTS} not found", *args, **kwargs
    ):
        super().__init__(message, *args, **kwargs)

    ui_error_message = f"The column {RECORD} or {MATCH_POINTS} was not found in the excel file. Please make sure to rename the column with the record or match points accordingly."


class InvalidRecordError(ValueError):
    def __init__(self, player_name, record, message="Invalid record", *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.ui_error_message = f"The record {record} of player {player_name} is invalid. Please make sure to specify the record in the format W-L-D."


class InvalidMatchPointsError(ValueError):
    def __init__(
        self, player_name, match_points, message="Invalid match points", *args, **kwargs
    ):
        super().__init__(message, *args, **kwargs)
        self.ui_error_message = f"The match points {match_points} of player {player_name} are invalid. Please make sure to specify the match points as a whole number."
