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

from bs4 import BeautifulSoup

from championship.parsers.parse_result import ParseResult

from .general_parser_functions import (
    find_index_containing_substring,
    parse_record,
    record_to_points,
)


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
