import datetime
from django.core.management.base import BaseCommand
from django.db.models import Count

from prettytable import PrettyTable
from championship.models import Event
from invoicing.models import fee_for_event


class Command(BaseCommand):
    help = "Report how many fees are paid in total per organizer "

    def handle(self, *args, **kwargs):
        table = PrettyTable(field_names=["Organizer", "Event", "Fee"], align="l")
        table.align["Fee"] = "r"
        total = 0

        for e in (
            Event.objects.exclude(category=Event.Category.REGULAR)
            .filter(date__lte=datetime.date.today())
            .order_by("organizer__name", "date")
        ):
            fee = fee_for_event(e)
            table.add_row((e.organizer.name, str(e), fee))
            total += fee

        table.add_row(("Total", "", total))
        print(table)
