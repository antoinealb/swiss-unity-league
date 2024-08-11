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


class Command(BaseCommand):
    help = "Report on number of player and events by format"

    def handle(self, *args, **kwargs):
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
