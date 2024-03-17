import collections
import itertools

from django.core.management.base import BaseCommand
from django.db.models import Count

from prettytable import PrettyTable

from championship.models import *
from championship.score.generic import get_leaderboard, get_results_with_qps
from championship.season import SEASON_LIST_WITH_ALL, find_season_by_slug


class Command(BaseCommand):
    help = (
        "Report on how on average players got their entry (through regular or whatever)"
    )

    def add_arguments(self, parser):
        all_seasons = ",".join(s.slug for s in SEASON_LIST_WITH_ALL)
        parser.add_argument(
            "--season",
            "-s",
            default=settings.DEFAULT_SEASON.slug,
            choices=[s.slug for s in SEASON_LIST_WITH_ALL],
            help=f"Season to report fees. Can be one of [{all_seasons}]",
        )
        parser.add_argument(
            "--top",
            default=40,
            type=int,
            help="Number of players to consider",
        )

    def handle(self, season, top, *args, **kwargs):
        season = find_season_by_slug(season)

        table = PrettyTable(
            field_names=["Name", "Regular", "Regional", "Premier"], align="r"
        )
        table.align["Name"] = "l"

        leaderboard = get_leaderboard(season)[:top]
        points_per_player_per_category = {
            p: {
                Event.Category.REGULAR: 0,
                Event.Category.REGIONAL: 0,
                Event.Category.PREMIER: 0,
            }
            for p in leaderboard
        }

        for result, score in get_results_with_qps(
            EventPlayerResult.objects.filter(
                event__date__gte=season.start_date,
                event__date__lte=season.end_date,
                player__in=leaderboard,
            )
            .select_related("player")
            .exclude(event__category=Event.Category.OTHER)
        ):
            points_per_player_per_category[result.player][
                result.event.category
            ] += score.qps

        for player in leaderboard:
            table.add_row(
                (
                    player.name,
                    points_per_player_per_category[player][Event.Category.REGULAR],
                    points_per_player_per_category[player][Event.Category.REGIONAL],
                    points_per_player_per_category[player][Event.Category.PREMIER],
                )
            )

        total_per_category = {
            k: sum(p[k] for p in points_per_player_per_category.values())
            for k in [
                Event.Category.REGULAR,
                Event.Category.REGIONAL,
                Event.Category.PREMIER,
            ]
        }
        table.add_row(
            (
                "Total",
                total_per_category[Event.Category.REGULAR],
                total_per_category[Event.Category.REGIONAL],
                total_per_category[Event.Category.PREMIER],
            )
        )
        total = sum(total_per_category.values())
        table.add_row(
            (
                "Total (%)",
                "{:.1f} %".format(
                    100 * total_per_category[Event.Category.REGULAR] / total
                ),
                "{:.1f} %".format(
                    100 * total_per_category[Event.Category.REGIONAL] / total
                ),
                "{:.1f} %".format(
                    100 * total_per_category[Event.Category.PREMIER] / total
                ),
            )
        )

        print(table)
