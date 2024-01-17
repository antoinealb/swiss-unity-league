import itertools

from django.core.management.base import BaseCommand
from django.db.models import Count

from prettytable import PrettyTable
from championship.models import *


class Command(BaseCommand):
    help = "Report on number of player and events by format"

    def handle(self, *args, **kwargs):
        players_by_format = []

        table = PrettyTable(field_names=["Format", "Registrations Count"], align="l")
        for entry in (
            Event.objects.all()
            .values("format")
            .annotate(player_count=Count("player"))
            .order_by("-player_count")
        ):
            table.add_row((entry["format"], entry["player_count"]))
        print(table)

        table = PrettyTable(field_names=["Format", "Event Count"], align="l")
        for entry in (
            Event.objects.all()
            .values("format")
            .annotate(event_count=Count("id"))
            .order_by("-event_count")
        ):
            table.add_row((entry["format"], entry["event_count"]))
        print(table)
