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

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Coalesce

from championship.models import Event, Player, PlayerSeasonData
from championship.seasons.definitions import EU_SEASONS, Season
from championship.seasons.helpers import find_main_season_by_date, find_season_by_slug


def assign_country_to_player(player: Player, season: Season):
    most_played_country = (
        Event.objects.filter(
            result__player=player,
        )
        .exclude(
            category=Event.Category.GRAND_PRIX,
        )
        .in_season(season)
        .distinct()
        .annotate(
            country=Coalesce("address__country", "organizer__default_address__country")
        )
        .exclude(country__isnull=True)
        .values("country")
        .annotate(event_count=Count("country"))
        .order_by("-event_count")
        .first()
    )
    if most_played_country:
        PlayerSeasonData.objects.update_or_create(
            player=player,
            season_slug=season.slug,
            defaults={
                "country": most_played_country["country"],
            },
        )


class Command(BaseCommand):
    help = "To each players' seasonal data we assign the country they played most local and regional events in the season."

    def add_arguments(self, parser):
        parser.add_argument(
            "--season",
            "-s",
            default=find_main_season_by_date(datetime.date.today()).slug,
            choices=[s.slug for s in EU_SEASONS],
            help="The season to which we apply the country to the players' season data.",
        )

    def handle(self, season, *args, **kwargs):
        season = find_season_by_slug(season)

        for player in Player.objects.exclude(
            playerseasondata__season_slug=season.slug,
            playerseasondata__auto_assign_country=False,
        ):
            assign_country_to_player(player, season)
