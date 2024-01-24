import math
import re
from typing import Tuple, cast
from parsita import ParserContext, reg, longest, lit, Failure, Success
from collections.abc import Iterable
from parsita.util import constant

RECORD_DELIMITERS = ["-", "–", "—", "/", ",", "_"]


def _fixed_separator(previous_state):
    return lit(previous_state[0]) > constant(previous_state[1])


class RecordParser(ParserContext, whitespace=r"[ \t]*"):  # type: ignore
    integer = reg(r"[0-9]+") > int
    separator = longest(*(lit(s) for s in RECORD_DELIMITERS))
    record_no_draw = (integer << separator) & integer
    record_draw = integer & (separator & integer >= _fixed_separator) & integer
    record = record_draw | (record_no_draw > (lambda d: d + [0]))


def parse_record(record: str) -> Tuple[int, int, int]:
    """Takes a record as a string an extract it into (win, loss, draws).

    :raises ValueError: If the string is not a correct record, with an error message.
    :returns The parsed tuple

    >>> parse_record('1-2-3')
    (1, 2, 3)
    >>> parse_record('2/1')
    (2, 1, 0)
    """

    result = RecordParser.record.parse(record)

    if isinstance(result, Failure):
        raise ValueError(result.failure())

    return cast(Tuple[int, int, int], tuple(result.unwrap()))


def record_to_points(record: str) -> int:
    """Computes how many points the given record should provide.

    :raises ValueError if we could not parse the provided record.

    >>> record_to_points('2-0')
    6
    """
    r = parse_record(record)
    return 3 * r[0] + 1 * r[2]


def estimate_rounds(match_point_list: list[int]):
    """Estimates the number of rounds based on a list of the match point of all players participating in a given tournament."""
    num_players = len(match_point_list)

    # The number of rounds needs to be at least the amount wins + draws of an individual player
    min_num_rounds = max([mp // 3 + mp % 3 for mp in match_point_list])

    # We add +1 because the actual rounds is likely to be 1 higher
    byes = min_num_rounds + 1 if num_players % 2 == 1 else 0

    total_wins = sum([mp // 3 for mp in match_point_list]) - byes
    total_losses = total_wins
    total_draws = sum([mp % 3 for mp in match_point_list])

    # We can estimate the number of rounds played based on the total number of wins, losses, draws and byes
    number_of_matches_per_player = (
        total_wins + total_draws + total_losses + byes
    ) / num_players

    # We round it up, since some players might drop out
    rounds_estimate = math.ceil(number_of_matches_per_player)

    return max(rounds_estimate, min_num_rounds)


def find_index_containing_substring(
    strings: Iterable[str], substrings: list[str]
) -> int | None:
    """Finds the index of the first element that contains one of the substring."""
    for index, value in enumerate(strings):
        for substring in substrings:
            if substring.strip() in value:
                return index
    return None


def find_record_index(strings: Iterable[str]) -> int | None:
    """Finds the first entry in a win-loss-draw format and return its index.

    >>> find_record_index(['foo', 'bar'])
    >>> find_record_index(['foo', 'bar', '1-2-3'])
    2
    """
    for index, entry in enumerate(strings):
        result = RecordParser.record_draw.parse(entry)
        if isinstance(result, Success):
            return index
    return None


def find_non_numeric_index(strings: Iterable[str]) -> int | None:
    """Finds the first entry which does not represent a number (float or int)."""
    expr = re.compile(r"[0-9]+(\.[0-9]*)?")
    for index, entry in enumerate(strings):
        if not expr.match(entry):
            return index
    return None


def find_index_of_nth_integer(strings: Iterable[str], n: int) -> int | None:
    """Finds the n-th element that can be converted to an int."""
    count = 0
    for i, value in enumerate(strings):
        if _check_string_contains_int(value):
            count += 1
            if count == n:
                return i
    return None


def _check_string_contains_int(string: str) -> bool:
    """Checks whether the provided string is a representation of an int."""
    result = RecordParser.integer.parse(string)
    return isinstance(result, Success)
