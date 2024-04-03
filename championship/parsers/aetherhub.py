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

from championship.parsers.general_parser_functions import parse_record
from championship.parsers.parse_result import ParseResult

AH_URL = "https://aetherhub.com"


def _standings(soup):
    matchs = soup.find(id="tab_results").find("tbody")

    def _value(row, name):
        return row[col_idxs[name]].text.rstrip().strip()

    def _get_decklist_url(row):
        try:
            deck_url = row[col_idxs["Deck"]].a.get("href")
            return AH_URL + deck_url
        except (AttributeError, KeyError):
            return None

    thead = soup.find(id="tab_results").find("thead")

    col_idxs = {
        cell.text.rstrip().strip(): i for i, cell in enumerate(thead.find_all("th"))
    }

    for row in matchs.find_all("tr"):
        row = [s for s in row.find_all("td")]
        name = _value(row, "Name")
        points = int(_value(row, "Points"))
        record = parse_record(_value(row, "Results"))
        decklist_url = _get_decklist_url(row)
        yield ParseResult(
            name=name,
            points=points,
            record=record,
            decklist_url=decklist_url,
        )


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
