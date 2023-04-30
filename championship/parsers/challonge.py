import re
from bs4 import BeautifulSoup
from .general_parser_functions import *


def _remove_brackets(text):
    return re.sub(r"\([^()]*\)", "", text)


def _get_player_and_record_index(table):
    titles = [tag.text.strip() for tag in table.find("thead").find_all("th")]
    player_index = find_index_of_substring(titles, "Participant")
    record_index = find_index_of_substring(titles, "Match W-L-T")

    if None in [player_index, record_index]:
        tbody = table.find("tbody").find_all("tr")
        first_row = [tag.text.strip() for tag in tbody[0].find_all(["th", "td"])]
        if player_index is None:
            player_index = find_non_numeric_index(first_row)
        if record_index is None:
            record_index = find_record_index(first_row)

    return player_index, record_index


def _check_tournament_swiss(soup):
    meta_data = soup.find("ul", class_="meta inline-meta-list -themed is-hidden-mobile")
    for item in meta_data.find_all("li", {"class": "item"}):
        if item.find("i", {"class": "icon fa fa-trophy"}):
            tournament_type = item.find("div", class_="text").text
    if tournament_type != "Swiss":
        raise ValueError("Tournament is not a Swiss tournament")


def _standings(soup):
    _check_tournament_swiss(soup)

    table = soup.find("table", class_="striped-table -light limited_width standings")
    player_index, record_index = _get_player_and_record_index(table)
    for line in table.find("tbody").find_all("tr"):
        values = [tag.text.strip() for tag in line.find_all(["th", "td"])]
        name = _remove_brackets(values[player_index]).strip()
        points = record_to_points(values[record_index])
        yield (name, points)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
