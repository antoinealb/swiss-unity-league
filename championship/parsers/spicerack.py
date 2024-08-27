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

from championship.parsers.parse_result import ParseResult


def parse_rounds_json(phases_json):
    for phase in reversed(phases_json):
        if phase["round_type"] == "SWISS":
            if phase["status"] != "COMPLETE":
                raise ValueError("Last Swiss phase is not complete")
            return phase["rounds"][-1]
    raise ValueError("No Swiss phase/round found")


def _standings(standings_json, total_rounds):
    for standing in standings_json:
        points = standing["points"]
        matches_drawn = points % 3
        matches_won = points // 3
        matches_lost = total_rounds - matches_won - matches_drawn
        yield ParseResult(
            name=standing["player"]["best_identifier"],
            points=points,
            record=(matches_won, matches_lost, matches_drawn),
        )


def parse_standings_json(round_json, total_rounds):
    if round_json["status"] != "COMPLETE":
        raise ValueError("Round is not complete")
    standings = list(_standings(round_json["standings"], total_rounds))
    return standings


def extract_event_id_from_url(url):
    url_re = r"https://www\.spicerack\.gg/[a-zA-Z/]+/(\d+)(?:/[a-zA-Z/]*)?"
    if match := re.match(url_re, url):
        return match.group(1)
