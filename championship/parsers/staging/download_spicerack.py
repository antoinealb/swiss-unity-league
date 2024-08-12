#!/usr/bin/env python3
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

"""
Exports Spicerack.gg data into CSV for import into unityleague.ch

The reason we are not doing this via a parser/importer and expose it on the
website is that the Spicerack people told us their API will change massively in
the coming weeks/months/year and we should not rely on it. In addition, nobody
else in Switzerland appears to be using Spicerack, except for us (Leonin League).

Known limitations:

    - Only supports events with top8
    - Makes a lot of assumptions about how the API works (reverse engineering)
    - Does not export top 8 data, which needs to be manually added.
"""

import argparse
import csv
import logging
from collections.abc import Iterable
from typing import TypeAlias

import requests

Name: TypeAlias = str
Result: TypeAlias = tuple[int, int, int]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id", type=int)
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_const",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument("--output", "-o", type=argparse.FileType("w"), default="-")
    parser.add_argument(
        "--top8", help="Correct for top8 in results", action="store_true"
    )

    return parser.parse_args()


def get_last_swiss_standings_id(event: int) -> int:
    "Returns the Standings ID for the last round of Swiss f r the given event ID."
    url = f"https://hydra.spicerack.gg/api/magic-events/{event}/get_all_rounds/"
    logging.debug("Fetching %s", url)
    resp = requests.get(url)
    resp.raise_for_status()

    rounds = sorted(resp.json(), key=lambda s: s["order_in_phases"])

    # Take the last round without a cut to top N
    for r in rounds:
        if r["rank_required_to_enter_phase"] is not None:
            break
        last_round = r

    return last_round["rounds"][-1]["id"]


def get_finals_standings_id(id: int) -> int:
    "Returns the standings ID after top 8"
    url = f"https://hydra.spicerack.gg/api/magic-events/{id}/get_all_rounds/"
    logging.debug("Fetching %s", url)
    resp = requests.get(url)
    resp.raise_for_status()

    # Take the last phase
    rounds = sorted(resp.json(), key=lambda s: s["order_in_phases"])[-1]["rounds"]
    return rounds[-1]["id"]


def get_standings(standings_id: int) -> Iterable[tuple[Name, Result]]:
    url = f"https://hydra.spicerack.gg/api/tournament-rounds/{standings_id}/include_all_standings/"
    resp = requests.get(url)
    resp.raise_for_status()

    for s in resp.json()["standings"]:
        if not s["user_event_status"]:
            continue
        win = s["user_event_status"]["matches_won"]
        loss = s["user_event_status"]["matches_lost"]
        draw = s["user_event_status"]["matches_drawn"]
        name = s["name_to_use"]

        yield (name, (win, loss, draw))


def get_standings_player(standings_id: int) -> list[Name]:
    """Similar as get_standings, but only returns a list of players name.

    The reason for this is that Spicerack API will not include W/L/D for
    players who are not in the tournament anymore, but some information can be
    extracted from their standings, including where they are in the top8 tree.
    """
    url = f"https://hydra.spicerack.gg/api/tournament-rounds/{standings_id}/include_all_standings/"
    resp = requests.get(url)
    resp.raise_for_status()

    return [s["name_to_use"] for s in resp.json()["standings"]]


def get_playoff_correction(event: int) -> dict[Name, Result]:
    """Returns how many points should be substracted from a player's record.

    Players who made it into top8 have 'too many points', as their top8 matches
    are included in the record, unlike what the SUL expects.
    """
    correction = dict()
    standings = get_standings_player(get_finals_standings_id(event))

    logging.debug("Extracted %d standings for correction", len(standings))

    standings = iter(standings)

    correction[next(standings)] = (-3, 0, 0)
    correction[next(standings)] = (-2, -1, 0)

    for _ in range(2):
        correction[next(standings)] = (-1, -1, 0)

    for _ in range(4):
        correction[next(standings)] = (0, -1, 0)

    return correction


def get_corrected_standings(
    event: int, correct_standings: bool
) -> Iterable[tuple[Name, Result]]:
    last_round_id = get_last_swiss_standings_id(event)
    logging.debug("Last Swiss standings ID appears to be %d", last_round_id)

    standings = list(get_standings(last_round_id))
    logging.info("Extracted %d players", len(standings))

    if correct_standings:
        correction = get_playoff_correction(event)
        logging.debug("top8 correction: %s", correction)
    else:
        logging.info("Not correcting for top8")
        correction = dict()

    for name, (w, l, d) in standings:
        try:
            dw, dl, dd = correction[name]
            w += dw
            l += dl
            d += dd
        except KeyError:
            pass

        yield name, (w, l, d)


def main():
    args = parse_args()
    logging.basicConfig(level=args.verbose)

    standings = get_corrected_standings(args.id, args.top8)

    writer = csv.DictWriter(args.output, ["PLAYER_NAME", "RECORD"])
    writer.writeheader()

    for name, (win, loss, draw) in standings:
        row = {"PLAYER_NAME": name, "RECORD": f"{win}-{loss}-{draw}"}
        writer.writerow(row)


if __name__ == "__main__":
    main()
