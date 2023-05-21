def record_to_points(record):
    points = 0
    for index, num in enumerate(record.split("-")):
        if index == 0:
            points += int(num) * 3
        if index == 2:
            points += int(num)
    return points


def find_index_with_substring(values, substrings):
    """
    Takes a list of values and finds the first index of the element that contains one of the substrings.
    """
    for index, value in enumerate(values):
        for substring in substrings:
            if substring.strip() in value:
                return index


def find_record_index(values):
    """
    Takes a list of values and finds index of first element that is a Swiss system record. (Three integers with a dash in between e.g. 3-0-1)
    """
    for index, entry in enumerate(values):
        records = entry.split("-")
        if len(records) == 3:
            return index


def find_non_numeric_index(values):
    """
    Takes a list of values and finds the index of the first element that's not a number.
    """
    for index, value in enumerate(values):
        try:
            float(value)
        except (ValueError, TypeError):
            return index


def find_index_of_nth_integer(values, n):
    """
    Takes a list of values and finds the index of the n-th integer it finds.
    """
    count = 0
    for i, value in enumerate(values):
        try:
            if int(value) == float(value):
                count += 1
                if count == n:
                    return i
        except (ValueError, TypeError):
            pass
