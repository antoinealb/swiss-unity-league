import random

from django.db import transaction
from django.core.management.base import BaseCommand

from championship.models import *
from championship.factories import *
import factory


class Command(BaseCommand):
    help = "Generates test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--organizers_count",
            type=int,
            default=3,
            help="Number of organizers to generate (default 3)",
        )
        parser.add_argument(
            "--events_count",
            type=int,
            default=10,
            help="Number of events to generate (default 10)",
        )
        parser.add_argument(
            "--players_count",
            type=int,
            default=50,
            help="Number of players to generate (default 50)",
        )

    @transaction.atomic
    def handle(self, players_count, organizers_count, events_count, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        models = [EventPlayerResult, Player, Event, EventOrganizer]
        for m in models:
            m.objects.all().delete()

        self.stdout.write("Creating new data...")

        organizers = [EventOrganizerFactory() for _ in range(organizers_count)]
        players = [PlayerFactory() for _ in range(players_count)]

        events = []
        for _ in range(events_count):
            e = EventFactory(organizer=random.choice(organizers))
            events.append(e)

        for event in events:
            random.shuffle(players)
            for i, p in enumerate(players):
                if i < len(players) // 2:
                    points = 9
                    w, l = 3, 1
                else:
                    points = 3
                    w, l = 1, 3
                EventPlayerResult.objects.create(
                    points=points,
                    player=p,
                    event=event,
                    ranking=i + 1,
                    win_count=w,
                    loss_count=l,
                    draw_count=0,
                )

        today = datetime.date.today()
        for _ in range(10):
            EventFactory(
                date=factory.Faker(
                    "date_between",
                    start_date=today,
                    end_date=today + datetime.timedelta(days=14),
                )
            )
