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


from django.core.management.base import BaseCommand
from django.db.models import Count

from prettytable import PrettyTable

from championship.models import Event
from championship.seasons.helpers import (
    find_season_by_slug,
    get_all_seasons,
    get_default_season,
)
from invoicing.models import fee_for_event


class Command(BaseCommand):
    help = "Report how many fees are paid in total per organizer"

    def add_arguments(self, parser):
        all_seasons = ",".join(s.slug for s in get_all_seasons())
        parser.add_argument(
            "--season",
            "-s",
            default=get_default_season().slug,
            choices=[s.slug for s in get_all_seasons()],
            help=f"Season to report fees. Can be one of [{all_seasons}]",
        )

    def handle(self, season, *args, **kwargs):
        table = PrettyTable(field_names=["Organizer", "Event", "Fee"], align="l")
        table.align["Fee"] = "r"
        total = 0
        season = find_season_by_slug(season)

        fee_per_organizer = {}

        for e in (
            Event.objects.exclude(category=Event.Category.REGULAR)
            .annotate(results_count=Count("result"))
            .filter(
                results_count__gt=0,
                date__lte=season.end_date,
                date__gte=season.start_date,
                include_in_invoices=True,
            )
            .order_by("organizer__name", "date")
        ):
            fee = fee_for_event(e)
            table.add_row((e.organizer.name, str(e)[:100], fee))
            total += fee
            fee_per_organizer[e.organizer] = fee_per_organizer.get(e.organizer, 0) + fee

        table.add_row(("Total", "", total))
        print(table)

        fee_per_organizer_table = PrettyTable(
            field_names=["Organizer", "Fee"], align="l"
        )

        for organizer, fee in fee_per_organizer.items():
            fee_per_organizer_table.add_row((organizer.name, fee))

        print(fee_per_organizer_table)
