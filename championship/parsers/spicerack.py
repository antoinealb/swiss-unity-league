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
from json import loads

from championship.parsers.parse_result import ParseResult


def parse_rounds_json(unparsed_json):
    phases_json = loads(unparsed_json)
    for phase in reversed(phases_json):
        if phase["round_type"] == "SWISS":
            if phase["status"] != "COMPLETE":
                raise ValueError("Last Swiss phase is not complete")
            return phase["rounds"][-1]
    raise ValueError("No Swiss phase/round found")


def _standings(soup, total_rounds):
    for standing in soup:
        points = standing["points"]
        matches_drawn = points % 3
        matches_won = points // 3
        matches_lost = total_rounds - matches_won - matches_drawn
        yield ParseResult(
            name=standing["player"]["best_identifier"],
            points=points,
            record=(matches_won, matches_lost, matches_drawn),
        )


def parse_standings_json(unparsed_json, total_rounds):
    round_json = loads(unparsed_json)
    if round_json["status"] != "COMPLETE":
        raise ValueError("Round is not complete")
    standings = list(_standings(round_json["standings"], total_rounds))
    return standings


def extract_event_id_from_url(url):
    url_re = r"https://www\.spicerack\.gg/[a-zA-Z/]+/(\d+)(?:/[a-zA-Z/]*)?"
    event_id = re.match(url_re, url)
    if event_id:
        return event_id.group(1)
