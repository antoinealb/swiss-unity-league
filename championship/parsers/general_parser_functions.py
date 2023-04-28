def record_to_points(record):
    points = 0
    for index, num in enumerate(record.split("-")):
        if index == 0:
            points += int(num) * 3
        if index == 2:
            points += int(num)
    return points


def find_index_of_substring(table_row, substring):
    for index, elem in enumerate(table_row):
        if substring in elem:
            return index


def find_record_index(table_row):
    for index, entry in enumerate(table_row):
        records = entry.split("-")
        if len(records) == 3:
            return index


def find_non_numeric_index(row):
    for index, value in enumerate(row):
        try:
            float(value)
        except:
            return index
