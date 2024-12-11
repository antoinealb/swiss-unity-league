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

import argparse
import csv
import dataclasses
import logging

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

import requests

from championship.models import Event, Player, Result
from championship.season import ALL_SEASONS, SEASON_2024, find_season_by_slug
from decklists.models import Collection, Decklist

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


@dataclasses.dataclass
class ColumnsLookup:
    first_name: int
    last_name: int
    url: int
    archetype: int

    def parse_row(self, row):
        return (
            row[self.first_name].rstrip().strip(),
            row[self.last_name].rstrip().strip(),
            row[self.url],
            row[self.archetype],
        )


class Command(BaseCommand):
    help = "Import decklists from Swiss Magic Master 2025"
    output_transaction = True

    def add_arguments(self, parser):
        parser.add_argument(
            "--input_file",
            "-i",
            help="CSV file containing player response",
            required=True,
            type=argparse.FileType("r"),
        )
        parser.add_argument(
            "--format", "-f", choices=["modern", "legacy"], default="modern"
        )
        parser.add_argument(
            "--skip-moxfield",
            action="store_true",
            help="If true, skip connection to Moxfield and register a placeholder list instead.",
        )
        parser.add_argument(
            "--season",
            "-s",
            default=SEASON_2024.slug,
            choices=[s.slug for s in ALL_SEASONS],
            help="The season to use to find the SMM event",
        )

    def read_moxfield(self, moxfield_id: str) -> tuple[str, str]:
        url = f"https://api2.moxfield.com/v3/decks/all/{moxfield_id}"
        logging.info("Opening %s", url)
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        data = resp.json()
        mainboard = "\n".join(
            f'{k["quantity"]} {k["card"]["name"]}'
            for k in data["boards"]["mainboard"]["cards"].values()
        )

        sideboard = "\n".join(
            f'{k["quantity"]} {k["card"]["name"]}'
            for k in data["boards"]["sideboard"]["cards"].values()
        )
        return mainboard, sideboard

    def get_player(self, players: QuerySet[Player], first: str, last: str) -> Player:
        name1 = f"{first} {last}"
        name2 = f"{last} {first}"
        try:
            return Player.objects.get_by_name(name1)
        except Player.DoesNotExist as e:
            try:
                return Player.objects.get_by_name(name2)
            except Player.DoesNotExist:
                raise e

    def handle(self, input_file, format, skip_moxfield, season, *args, **kwargs):
        reader = csv.reader(input_file)

        season = find_season_by_slug(season)
        smm_events = Event.objects.filter(
            date__gte=season.start_date,
            date__lte=season.end_date,
            organizer__name="AarebogeMagic",
            category=Event.Category.PREMIER,
        )
        if format == "modern":
            lookup = ColumnsLookup(last_name=2, first_name=3, archetype=7, url=8)
            event = smm_events.get(format=Event.Format.MODERN)
        elif format == "legacy":
            lookup = ColumnsLookup(last_name=2, first_name=3, archetype=11, url=12)
            event = smm_events.get(format=Event.Format.LEGACY)

        collection, _ = Collection.objects.get_or_create(
            submission_deadline=event.date,
            publication_time=event.date,
            event=event,
        )

        Decklist.objects.filter(collection=collection).delete()
        Result.objects.filter(event=event).update(decklist_url="")

        players_id = [s[0] for s in event.result_set.values_list("player_id")]
        players = Player.objects.filter(id__in=players_id)

        # Skip header row
        next(reader)

        found_rows = 0
        total_rows = 0
        for row in reader:
            first, last, url, archetype = lookup.parse_row(row)

            if not url:
                continue

            total_rows += 1
            try:
                player = self.get_player(players, first, last)
                found_rows += 1
            except Player.DoesNotExist:
                logging.warning("Could not find player %s %s, skipping...", first, last)
                continue

            try:
                result = Result.objects.get(event=event, player=player)
            except Result.DoesNotExist:
                logging.warning("No result for %s, skipping...", player.name)

            if skip_moxfield:
                mainboard = "4 Fry"
                sideboard = "4 Okk"
            else:
                moxfield_id = url.split("/")[-1]
                # TODO: HTTP error handling
                try:
                    mainboard, sideboard = self.read_moxfield(moxfield_id)
                except requests.HTTPError:
                    logging.warning(
                        "Could not open decklist for player %s (%s), skipping...",
                        player.name,
                        moxfield_id,
                    )
                    continue

            dl, _ = Decklist.objects.get_or_create(
                collection=collection,
                player=player,
            )
            dl.archetype = archetype
            dl.mainboard = mainboard
            dl.sideboard = sideboard
            dl.save()

            result.decklist = dl
            result.save()

        print(f"Found {found_rows} players out of {total_rows} rows")
