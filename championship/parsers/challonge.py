# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

from bs4 import BeautifulSoup

from championship.parsers.parse_result import ParseResult

from .general_parser_functions import *


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
    meta_data = soup.find("ul", class_="redesigned-meta-list")
    for item in meta_data.find_all("li", {"class": "item"}):
        if item.find("div", {"class": "item-label"}).text == "Format":
            tournament_type = item.find("div", class_="text").text
    if tournament_type != "Swiss":
        raise TournamentNotSwissError()


def _standings(soup):
    _check_tournament_swiss(soup)

    table = soup.find("table", class_="striped-table -light limited_width standings")
    player_index, record_index, bye_index = _get_indices(table)
    for line in table.find("tbody").find_all("tr"):
        cells = line.find_all(["th", "td"])
        values = [tag.text.strip() for tag in cells]
        name = _remove_brackets(values[player_index]).strip()
        points = record_to_points(values[record_index])
        record = list(parse_record(values[record_index]))

        # If a player drops (class=removed), challonge gives them a bye for each round they missed.
        # Hence the player gets too many points. So we should only count byes if the player has not dropped.
        player_dropped = "removed" in cells[player_index].get("class", [])
        if not player_dropped:
            byes = int(values[bye_index])
            points += byes * 3
            # Store the byes as wins
            record[0] += byes

        yield ParseResult(
            name=name,
            points=points,
            record=tuple(record),
        )


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
    for tourney_id in path.split("/"):
        if 7 <= len(tourney_id) <= 9:
            return https + challonge + tourney_id + "/standings"
    raise ValueError("No tournament id found")


class TournamentNotSwissError(ValueError):
    def __init__(self, message="Tournament is not Swiss.", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

    ui_error_message = "The tournament you are trying to upload is not played with Swiss rounds. Only Swiss rounds tournaments can be uploaded."
