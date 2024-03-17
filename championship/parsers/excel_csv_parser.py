import pandas as pd

from championship.parsers.general_parser_functions import (
    estimate_rounds,
    parse_record,
    record_to_points,
)
from championship.parsers.parse_result import ParseResult

PLAYER_NAME = "PLAYER_NAME"
RECORD = "RECORD"
MATCH_POINTS = "MATCH_POINTS"


def _standings(df: pd.DataFrame):
    defined_cols = [
        col for col in [PLAYER_NAME, RECORD, MATCH_POINTS] if col in df.columns
    ]
    df = df[defined_cols]

    if PLAYER_NAME not in defined_cols:
        raise PlayerNameNotFound()

    df = df.dropna(subset=[PLAYER_NAME])
    if RECORD in defined_cols:
        for _, row in df.iterrows():
            name = row[PLAYER_NAME]
            record_string = row[RECORD]
            try:
                parsed_record = parse_record(record_string)
                points = record_to_points(record_string)
            except ValueError:
                raise InvalidRecordError(name, record_string)
            yield ParseResult(name=name, points=points, record=parsed_record)
    elif MATCH_POINTS in defined_cols:
        name_points_tuple_list = []
        for _, row in df.iterrows():
            try:
                name_points_tuple_list.append(
                    (row[PLAYER_NAME], int(row[MATCH_POINTS]))
                )
            except:
                raise InvalidMatchPointsError(row[PLAYER_NAME], row[MATCH_POINTS])
        match_points_list = [points for _, points in name_points_tuple_list]
        num_rounds = estimate_rounds(match_points_list)
        for name, points in name_points_tuple_list:
            wins = points // 3
            draws = points % 3
            losses = num_rounds - wins - draws
            yield ParseResult(name=name, points=points, record=(wins, losses, draws))
    else:
        raise RecordOrMatchPointsNotFound()


def parse_standings_page(df: pd.DataFrame):
    return list(_standings(df))


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
