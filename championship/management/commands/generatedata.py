import random

from django.db import transaction
from django.core.management.base import BaseCommand

from championship.models import *
from championship.factories import *

N_ORGANIZERS = 3
N_EVENTS = 100
N_PLAYERS = 50


class Command(BaseCommand):
    help = "Generates test data"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        models = [EventPlayerResult, Player, Event, EventOrganizer]
        for m in models:
            m.objects.all().delete()

        self.stdout.write("Creating new data...")

        organizers = [EventOrganizerFactory() for _ in range(N_ORGANIZERS)]
        players = [PlayerFactory() for _ in range(N_PLAYERS)]

        events = []
        for _ in range(N_EVENTS):
            e = EventFactory(organizer=random.choice(organizers))
            events.append(e)

        for event in events:
            random.shuffle(players)
            for i, p in enumerate(players):
                EventPlayerResult.objects.create(ranking=i + 1, player=p, event=event)
