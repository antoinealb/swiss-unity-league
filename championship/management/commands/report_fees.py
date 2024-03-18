import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count

from prettytable import PrettyTable

from championship.models import Event
from championship.season import SEASON_LIST_WITH_ALL, find_season_by_slug
from invoicing.models import fee_for_event


class Command(BaseCommand):
    help = "Report how many fees are paid in total per organizer "

    def add_arguments(self, parser):
        all_seasons = ",".join(s.slug for s in SEASON_LIST_WITH_ALL)
        parser.add_argument(
            "--season",
            "-s",
            default=settings.DEFAULT_SEASON.slug,
            choices=[s.slug for s in SEASON_LIST_WITH_ALL],
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
