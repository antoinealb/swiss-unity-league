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

from typing import Iterator

from django.core.management.base import BaseCommand
from django.db.models import Count, Max

import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

from championship.models import Event
from championship.seasons.definitions import SEASON_2023, SEASON_2024, Season
from championship.seasons.helpers import get_all_seasons
from invoicing.models import Invoice, fee_for_event


def discount_for_season(season: Season) -> int:
    invoices = Invoice.objects.filter(
        start_date__gte=season.start_date, end_date__lte=season.end_date
    )
    return sum(s.discount for s in invoices)


def data_points_for_season(season: Season) -> Iterator[tuple[int, int]]:
    events = (
        Event.objects.filter(
            category__in=[Event.Category.PREMIER, Event.Category.REGIONAL],
            date__gte=season.start_date,
            date__lte=season.end_date,
        )
        .annotate(result_cnt=Count("result"))
        .exclude(result_cnt=0)
        .order_by("date")
    )

    revenue = 0
    for event in events:
        days_since_start = (event.date - season.start_date).days
        revenue += fee_for_event(event)
        yield days_since_start, revenue


def plot_title():
    date = (
        Event.objects.filter(
            category__in=[Event.Category.PREMIER, Event.Category.REGIONAL]
        )
        .annotate(result_cnt=Count("result"))
        .exclude(result_cnt=0)
        .aggregate(Max("date"))["date__max"]
    )
    date = date.strftime("%Y-%m-%d")
    return f"Evolution of SUL revenue per season (ignoring discounts)\nas of {date}"


class Command(BaseCommand):
    help = "Plot our revenue over time, allowing us to compare seasons."

    def add_arguments(self, parser):
        all_seasons = ",".join(s.slug for s in get_all_seasons())
        parser.add_argument(
            "--season",
            "-s",
            default=[SEASON_2023, SEASON_2024],
            action="append",
            choices=[s.slug for s in get_all_seasons()],
            help=f"Season to report fees. Can be one of [{all_seasons}]",
        )
        parser.add_argument(
            "--output", "-o", help="File to save the plot to", required=True
        )

    def handle(self, season, output, *args, **kwargs):
        plt.figure()
        legends = []
        for s in season:
            legends.append(s.name)
            data = list(data_points_for_season(s))
            x, y = list(zip(*data))
            plt.plot(x, y, "-")

        plt.gca().yaxis.set_major_formatter(FormatStrFormatter("%d CHF"))

        plt.title(plot_title())
        plt.ylabel("Revenue")
        plt.xlabel("Days since season start")
        plt.legend(legends)
        plt.tight_layout()
        plt.savefig(output)
