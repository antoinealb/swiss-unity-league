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

from django.core.management.base import BaseCommand

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
            required=True,
        )

    def handle(self, scryfall_dump, *args, **kwargs):
        # Unit tests require this to be a string
        if isinstance(scryfall_dump, str):
            scryfall_dump = open(scryfall_dump)
        data = json.load(scryfall_dump)

        Card.objects.all().delete()

        cards = [
            Card(
                oracle_id=entry["oracle_id"],
                name=entry["name"],
                mana_cost=entry.get("mana_cost", ""),
                scryfall_uri=entry["scryfall_uri"],
                mana_value=int(entry.get("cmc", 0)),
            )
            for entry in data
            if is_valid(entry)
        ]
        Card.objects.bulk_create(cards)
