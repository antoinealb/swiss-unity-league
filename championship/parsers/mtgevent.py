from bs4 import BeautifulSoup

from championship.parsers.parse_result import ParseResult
from .general_parser_functions import *


def _standings(soup):
    table = soup.find(
        "table", {"class": "MuiTable-root", "aria-label": "Results table"}
    )
    titles = [tag.text.strip() for tag in table.find("thead").find_all("th")]
    player_index = find_index_containing_substring(titles, ["Player"])
    record_index = find_index_containing_substring(titles, ["Record"])
    for line in table.find("tbody").find_all("tr"):
        values = [tag.text.strip() for tag in line.find_all(["th", "td"])]
        record = values[record_index]
        name = values[player_index]
        points = record_to_points(record)
        record = parse_record(record)

        yield ParseResult(
            name=name,
            points=points,
            record=record,
        )


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
