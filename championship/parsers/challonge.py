import re
from bs4 import BeautifulSoup
from .general_parser_functions import *


RECORD_REGEXP = re.compile(r"(\d+) - (\d+)(?: - (\d+))?")


def _remove_brackets(text):
    return re.sub(r"\([^()]*\)", "", text)


def _get_indices(table):
    titles = [tag.text.strip() for tag in table.find("thead").find_all("th")]
    player_index = find_index_containing_substring(titles, ["Participant"])
    record_index = find_index_containing_substring(titles, ["Match W-L-T"])
    bye_index = find_index_containing_substring(titles, ["Byes"])

    if None in [player_index, record_index, bye_index]:
        tbody = table.find("tbody").find_all("tr")
        first_row = [tag.text.strip() for tag in tbody[0].find_all(["th", "td"])]
        if player_index is None:
            player_index = find_non_numeric_index(first_row)
        if record_index is None:
            record_index = find_record_index(first_row)
        if bye_index is None:
            bye_index = find_index_of_nth_integer(first_row, 2)

    return player_index, record_index, bye_index


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
    player_index, record_index, bye_index = _get_indices(table)
    for line in table.find("tbody").find_all("tr"):
        values = [tag.text.strip() for tag in line.find_all(["th", "td"])]
        name = _remove_brackets(values[player_index]).strip()
        points = record_to_points(values[record_index])

        m = RECORD_REGEXP.match(values[record_index])
        record = list(int(s or "0") for s in m.groups())

        byes = int(values[bye_index])
        points += byes * 3

        # Store the byes as wins
        record[0] += byes
        yield (name, points, tuple(record))


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings


def clean_url(url):
    challonge = "challonge.com/"
    https = "https://"
    try:
        url_start, path = url.split(challonge)
    except:
        raise ValueError("No challonge.com URL")
    if not url_start.startswith(https):
        url_start = https
    for tourney_id in path.split("/"):
        if len(tourney_id) == 8:
            return url_start + challonge + tourney_id + "/standings"
    raise ValueError("No tournament id found")
