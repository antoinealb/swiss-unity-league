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


def _standings(soup):
    standings = soup.find(class_="standings")
    if not standings:
        raise ValueError("No standings found")

    def clean(elem):
        return elem.text.rstrip().strip()

    for row in standings.find("tbody").find_all("tr"):
        name = clean(row.find(class_="name").string)
        points = int(clean(row.find(class_="points").string))
        win_loss_draw = parse_record(row.find(class_="wldb").string)
        yield ParseResult(
            name=name,
            points=points,
            record=win_loss_draw,
        )


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
