def record_to_points(record):
    points = 0
    for index, num in enumerate(record.split("-")):
        if index == 0:
            points += int(num) * 3
        if index == 2:
            points += int(num)
    return points


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
