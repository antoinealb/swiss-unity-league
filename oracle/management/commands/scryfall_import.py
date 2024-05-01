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
import json
import logging

from django.core.management.base import BaseCommand

import requests

from decklists.parser import parse_mana
from oracle.models import Card


def is_valid(entry):
    if entry.get("set_type", "") in ["memorabilia"]:
        return False

    # Remove cards that are legal in no formats
    if not any(v == "legal" for v in entry["legalities"].values()):
        return False

    return True


class Command(BaseCommand):
    help = "Import all cards from a Scryfall bulk data dump."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scryfall_dump",
            "-s",
            help="Oracle file downloaded from https://scryfall.com/docs/api/bulk-data",
            type=argparse.FileType(),
        )

    def load_data(self, path):
        if path:
            # Unit tests require this to be a string
            if isinstance(path, str):
                path = open(path)
            return json.load(path)

        # if no path was provided, instead fetch it from Scryfall directly
        logging.info("No local path provided, querying Scryfall")
        resp = requests.get("https://api.scryfall.com/bulk-data")
        resp.raise_for_status()

        data = resp.json()["data"]

        url = [s["download_uri"] for s in data if s["type"] == "oracle_cards"][0]
        data = requests.get(url)
        data.raise_for_status()

        return data.json()

    def handle(self, scryfall_dump, *args, **kwargs):
        data = self.load_data(scryfall_dump)

        Card.objects.all().delete()

        cards = [
            Card(
                oracle_id=entry["oracle_id"],
                name=entry["name"],
                mana_cost=entry.get("mana_cost", ""),
                scryfall_uri=entry["scryfall_uri"],
                mana_value=int(entry.get("cmc", 0)),
                type_line=entry["type_line"],
            )
            for entry in data
            if is_valid(entry)
        ]
        Card.objects.bulk_create(cards)
        logging.info("Imported %d cards", len(cards))

        invalid_mana_costs = set()
        for card in cards:
            if not card.mana_cost:
                continue
            try:
                parse_mana(card.mana_cost)
            except ValueError:
                invalid_mana_costs.add(card.mana_cost)
                logging.warning(f"Could not parse mana cost for '{card.name}'")

        if invalid_mana_costs:
            logging.warning("The following mana cost did not parse succesfully:")
            for c in sorted(invalid_mana_costs):
                logging.warning(c)
