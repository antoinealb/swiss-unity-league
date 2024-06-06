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

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count

from prettytable import PrettyTable

from championship.models import Event
from championship.season import ALL_SEASONS_LIST, find_season_by_slug
from invoicing.models import fee_for_event


class Command(BaseCommand):
    help = "Report how many fees are paid in total per organizer"

    def add_arguments(self, parser):
        all_seasons = ",".join(s.slug for s in ALL_SEASONS_LIST)
        parser.add_argument(
            "--season",
            "-s",
            default=settings.DEFAULT_SEASON.slug,
            choices=[s.slug for s in ALL_SEASONS_LIST],
            help=f"Season to report fees. Can be one of [{all_seasons}]",
        )

    def handle(self, season, *args, **kwargs):
        table = PrettyTable(field_names=["Organizer", "Event", "Fee"], align="l")
        table.align["Fee"] = "r"
        total = 0
        season = find_season_by_slug(season)

        for e in (
            Event.objects.exclude(category=Event.Category.REGULAR)
            .annotate(results_count=Count("eventplayerresult"))
            .filter(
                results_count__gt=0,
                date__lte=season.end_date,
                date__gte=season.start_date,
                include_in_invoices=True,
            )
            .order_by("organizer__name", "date")
        ):
            fee = fee_for_event(e)
            table.add_row((e.organizer.name, str(e), fee))
            total += fee

        table.add_row(("Total", "", total))
        print(table)
