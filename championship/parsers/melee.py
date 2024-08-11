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

import csv

from championship.parsers.parse_result import ParseResult


def parse_standings(text):
    reader = csv.DictReader(text.splitlines())

    # In Melee export, there can be several phases, and we will have standings
    # for every phase appended. We only take the last phase here.
    result_per_player = {}
    for line in reader:
        first, last = line["FirstName"], line["LastName"]
        wins = int(line["MatchWins"])
        loses = int(line["MatchLoses"])
        draws = int(line["MatchDraws"])
        points = int(line["Points"])
        rank = int(line["Rank"])
        name = f"{first} {last}"
        result_per_player[name] = (rank, name, points, (wins, loses, draws))

    # Now the dict contains deduplicate entries
    return [
        ParseResult(name, points, standings)
        for (rank, name, points, standings) in sorted(result_per_player.values())
    ]
