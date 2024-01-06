"""Season-independent logic for computing score.

The code in this file is mostly season-independent.
"""

from collections import defaultdict
from typing import Iterable, Any

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import Count
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from prometheus_client import Summary, Gauge

from championship.cache_function import cache_function
from championship.models import EventPlayerResult, Player
from championship.season import Season, SEASON_LIST

from championship.score import LeaderboardScore
from championship.score.season_2023 import ScoreMethod2023

scores_computation_time_seconds = Summary(
    "scores_computation_time_seconds", "Time spent to compute scores of all players"
)
scores_computation_results_count = Gauge(
    "scores_computation_results_count",
    "Number of EventPlayerResultUsed for computing the leaderboard.",
    ["season_id", "season_name"],
)


def get_results_with_qps(
    event_player_results: models.QuerySet[EventPlayerResult],
) -> Iterable[tuple[EventPlayerResult, Any]]:
    """
    Pass a QuerySet of EventPlayerResult, and get it annotated with the following fields:
    - has_top8: True if the event has a top8
    - qps: the number of QPs the player got in this event
    - event_size: the number of players in the event
    - event: the event
    - byes: Number of byes awarded for this result.
    """
    results = event_player_results.select_related("event").annotate(
        event_size=Count("event__eventplayerresult"),
        top_count=Count("event__eventplayerresult__single_elimination_result"),
    )

    for result in results:
        result.has_top8 = result.top_count > 0
        score = ScoreMethod2023.score_for_result(
            result, event_size=result.event_size, has_top8=result.has_top8
        )
        yield result, score


def _score_cache_key(season):
    return f"compute_scoresS{season.slug}"


@cache_function(cache_key=_score_cache_key)
@scores_computation_time_seconds.time()
def compute_scores(season: Season) -> dict[int, LeaderboardScore]:
    scores_by_player: dict[int, Any] = {}

    count = 0
    for result, score in get_results_with_qps(
        EventPlayerResult.objects.filter(
            event__date__gte=season.start_date,
            event__date__lte=season.end_date,
            player__in=Player.leaderboard_objects.all(),
        )
    ):
        count += 1

        try:
            scores_by_player[result.player_id] += score
        except KeyError:
            scores_by_player[result.player_id] = score

    scores_computation_results_count.labels(season.slug, season.name).set(count)

    return ScoreMethod2023.finalize_scores(scores_by_player)


@receiver(post_delete, sender=EventPlayerResult)
@receiver(pre_save, sender=EventPlayerResult)
def invalidate_score_cache(sender, **kwargs):
    for s in SEASON_LIST:
        cache.delete(_score_cache_key(s))


def get_leaderboard(season) -> list[Player]:
    """Returns a list of Player with their score.

    This function returns a list of Players with an additional score property
    (of type Score), containing all informations required to render a
    leaderboard.
    """
    scores_by_player = compute_scores(season)
    players_with_score = []
    for player in Player.leaderboard_objects.all():
        if score := scores_by_player.get(player.id):
            player.score = score
            players_with_score.append(player)
    players_with_score.sort(key=lambda l: l.score.rank)
    return players_with_score
