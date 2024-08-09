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
import logging
import random

from django.core.management.base import BaseCommand
from django.db import transaction

import factory

from championship.factories import EventFactory, EventOrganizerFactory, PlayerFactory
from championship.models import Event, EventOrganizer, Player, Result


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
        logging.info("Deleting old data...")
        models = [Result, Player, Event, EventOrganizer]
        for m in models:
            m.objects.all().delete()

        logging.info("Creating new data...")

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
                Result.objects.create(
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
