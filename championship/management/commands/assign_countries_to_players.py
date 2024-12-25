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

from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway
from waffle import sample_is_active

from championship.models import Event, Player, PlayerSeasonData
from championship.seasons.definitions import EU_SEASONS, Season
from championship.seasons.helpers import find_season_by_slug

metrics_registry = CollectorRegistry()
player_season_data_updated = Counter(
    "player_season_data_updated_count",
    "Number of PlayerSeasonData objects updated by the script run.",
    ["created"],
    registry=metrics_registry,
)
last_success = Gauge(
    "job_last_success_unixtime",
    "Last time a job finished succesfully",
    registry=metrics_registry,
)


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
    most_played_country = {"country": "CH"}
    if most_played_country:
        _, created = PlayerSeasonData.objects.update_or_create(
            player=player,
            season_slug=season.slug,
            defaults={
                "country": most_played_country["country"],
            },
        )
        player_season_data_updated.labels(created).inc()


class Command(BaseCommand):
    help = "To each players' seasonal data we assign the country they played most local and regional events in the season."

    def get_default_season(self):
        today = datetime.date.today()
        for season in EU_SEASONS:
            if season.start_date <= today <= season.end_date:
                return season

    def add_arguments(self, parser):
        parser.add_argument(
            "--season",
            "-s",
            default=self.get_default_season().slug,
            choices=[s.slug for s in EU_SEASONS],
            help="The season to which we apply the country to the players' season data.",
        )
        parser.add_argument(
            "--force-sampling",
            "-f",
            action="store_true",
            help="If set, force sampling, meaning all eligible players will be updated.",
        )
        parser.add_argument(
            "--pushgateway", help="Address to the Prometheus pushgateway"
        )

    def handle(self, season, force_sampling, pushgateway, *args, **kwargs):
        season = find_season_by_slug(season)

        # the parser doesn't check the default value
        assert season.slug in [
            s.slug for s in EU_SEASONS
        ], "This command only works for EU seasons."

        for player in Player.objects.exclude(
            playerseasondata__season_slug=season.slug,
            playerseasondata__auto_assign_country=False,
        ):
            if force_sampling or sample_is_active(
                "assign_countries_to_player_fraction"
            ):
                assign_country_to_player(player, season)

        last_success.set_to_current_time()
        if pushgateway:
            push_to_gateway(
                pushgateway, job="league-assign-countries", registry=metrics_registry
            )
