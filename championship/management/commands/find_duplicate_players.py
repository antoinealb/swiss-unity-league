import itertools
from difflib import SequenceMatcher

from django.core.management.base import BaseCommand

from prettytable import PrettyTable

from championship.models import *


def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class Command(BaseCommand):
    help = "Find players with similar names for merging them"

    def add_arguments(self, parser):
        parser.add_argument(
            "--threshold",
            "-t",
            type=float,
            default=0.85,
            help="Similarity threshold to display (default >0.85)",
        )

    def handle(self, threshold, *args, **kwargs):
        players = list(Player.objects.all())
        similarities = []
        visited = set()
        for p1, p2 in itertools.product(players, repeat=2):
            if p1 == p2:
                continue

            if (p1, p2) in visited or (p2, p1) in visited:
                continue

            visited.add((p1, p2))

            ratio = similar(p1.name, p2.name)

            if ratio >= threshold:
                similarities.append((ratio, p1.name, p2.name))

        # Sort by similarity
        similarities.sort(reverse=True)

        table = PrettyTable(field_names=["Similarity", "Player A", "Player B"])
        table.float_format = ".3"
        table.align = "l"
        for ratio, p1, p2 in similarities:
            table.add_row([ratio, p1, p2])

        print(table)
