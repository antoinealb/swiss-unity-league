import re
from bs4 import BeautifulSoup
from .general_parser_functions import (
    record_to_points,
    find_record_index,
    find_non_numeric_index,
)


def _removeBrackets(text):
    return re.sub(r"\([^()]*\)", "", text)


def _standings(soup):
    table = soup.find("table", class_="striped-table -light limited_width standings")
    tbody = table.find("tbody").find_all("tr")
    first_row = [tag.text.strip() for tag in tbody[0].find_all(["th", "td"])]
    player_index = find_non_numeric_index(first_row)
    record_index = find_record_index(first_row)
    for line in tbody:
        values = [tag.text.strip() for tag in line.find_all(["th", "td"])]
        name = _removeBrackets(values[player_index]).strip()
        points = record_to_points(values[record_index])
        yield (name, points)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
