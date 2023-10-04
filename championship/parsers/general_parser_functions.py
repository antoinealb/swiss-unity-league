from typing import Tuple, cast
from parsita import ParserContext, reg, longest, lit, Failure
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


def find_index_containing_substring(strings, substrings):
    """
    Takes a list of strings and finds the first index of the element that contains one of the substrings.
    """
    for index, value in enumerate(strings):
        for substring in substrings:
            if substring.strip() in value:
                return index


def find_record_index(strings):
    """
    Takes a list of strings and finds index of first element that is a Swiss system record. (Three integers with a dash in between e.g. 3-0-1)
    """
    for index, entry in enumerate(strings):
        record = entry.split("-")
        if len(record) == 3:
            all_are_integers = all(
                [_check_string_contains_int(value) for value in record]
            )
            if all_are_integers:
                return index


def find_non_numeric_index(strings):
    """
    Takes a list of strings and finds the index of the first element that's not a number (can't be converted to a float).
    """
    for index, value in enumerate(strings):
        try:
            float(value)
        except (ValueError, TypeError):
            return index


def find_index_of_nth_integer(strings, n):
    """
    Takes a list of strings and finds the index of the n-th element it finds that can be converted to an integer.
    """
    count = 0
    for i, value in enumerate(strings):
        if _check_string_contains_int(value):
            count += 1
            if count == n:
                return i


def _check_string_contains_int(string):
    """
    Checks whether the string contains an integer (it can be converted to an int).
    """
    try:
        if int(string) == float(string):
            return True
    except (ValueError, TypeError):
        return False
