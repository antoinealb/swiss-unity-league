import pandas as pd
from championship.parsers.general_parser_functions import parse_record, record_to_points


RANK = "RANK"
PLAYER_NAME = "PLAYER_NAME"
RECORD = "RECORD"
MATCH_POINTS = "MATCH_POINTS"


def _standings(df: pd.DataFrame):
    defined_cols = [
        col for col in [RANK, PLAYER_NAME, RECORD, MATCH_POINTS] if col in df.columns
    ]
    df = df[defined_cols]
    if RANK not in defined_cols:
        df[RANK] = df.index + 1
    if PLAYER_NAME not in defined_cols:
        raise PlayerNameNotFound()
    if RECORD not in defined_cols and MATCH_POINTS not in defined_cols:
        raise RecordOrMatchPointsNotFound()

    if RECORD in defined_cols:
        for _, row in df.iterrows():
            name = row[PLAYER_NAME]
            record_string = row[RECORD]
            try:
                parsed_record = parse_record(record_string)
                points = record_to_points(record_string)
            except ValueError:
                raise InvalidRecordError(name, record_string)
            yield (name, points, tuple(parsed_record))


def parse_standings_page(df: pd.DataFrame):
    standings = list(_standings(df))
    return standings


class PlayerNameNotFound(ValueError):
    def __init__(self, message="Column PLAYER_NAME not found", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

    ui_error_message = "The column PLAYER_NAME was not found in the excel file. Please make sure to specify the first and lastname of each player in the column PLAYER_NAME."


class RecordOrMatchPointsNotFound(ValueError):
    def __init__(
        self, message="Column RECORD or MATCH_POINTS not found", *args, **kwargs
    ):
        super().__init__(message, *args, **kwargs)

    ui_error_message = "The column RECORD or MATCH_POINTS was not found in the excel file. Please make sure to specify either the record or match points of each player in the column RECORD or MATCH_POINTS."


class InvalidRecordError(ValueError):
    def __init__(self, player_name, record, message="Invalid record", *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.ui_error_message = f"The record {record} of player {player_name} is invalid. Please make sure to specify the record in the format W-L-D."
