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
Fetches results from the UnityLeague API and translates into Excel
"""

import argparse
from csv import DictWriter
from urllib.parse import urljoin

import requests


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        "-u",
        help="Unityleague instance to use (e.g. 'https://unityleague.ch')",
        default="https://unityleague.ch/",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Where to write the output, default to standard output.",
        type=argparse.FileType("w", encoding="utf-8-sig"),
        default="-",
    )

    return parser.parse_args()


def fetch_events(url):
    url = urljoin(url, "/api/events/")
    resp = requests.get(url)
    resp.raise_for_status()
    events = resp.json()
    events = [e for e in events if e["category"] != "OTHER"]
    return sorted(events, key=lambda e: e["date"])


def main():
    args = parse_args()

    events = fetch_events(args.url)

    writer = DictWriter(
        args.output,
        [
            "date",
            "event",
            "type",
            "format",
            "player",
            "wins",
            "losses",
            "draws",
            "playoff_result",
        ],
    )
    writer.writeheader()

    for event in events:
        for result in event["results"]:
            row = {
                "date": event["date"],
                "event": event["name"],
                "type": event["category"],
                "format": event["format"],
                "player": result["player"],
                "wins": result["win_count"],
                "losses": result["loss_count"],
                "draws": result["draw_count"],
                "playoff_result": result["single_elimination_result"],
            }
            writer.writerow(row)


if __name__ == "__main__":
    main()
