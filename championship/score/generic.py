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

"""Season-independent logic for computing score.

The code in this file is mostly season-independent.
"""

from typing import Any, Iterable

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db import models
from django.db.models import Count, F, Max
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from prometheus_client import Gauge, Summary

from championship.cache_function import cache_function
from championship.models import Event, OrganizerLeague, Player, PlayerSeasonData, Result
from championship.score.eu_season_2025 import ScoreMethodEu2025
from championship.score.invitational_spring_2025 import (
    ScoreMethodInvitationalSpring2025,
)
from championship.score.season_2023 import ScoreMethod2023
from championship.score.season_2024 import ScoreMethod2024
from championship.score.season_2025 import ScoreMethod2025
from championship.score.season_all import ScoreMethodAll
from championship.score.types import LeaderboardScore
from championship.seasons.definitions import (
    EU_SEASON_2024_MOCKUP,
    EU_SEASON_2025,
    INVITATIONAL_SPRING_2025,
    SEASON_2023,
    SEASON_2024,
    SEASON_2025,
    SWISS_SEASON_ALL,
    Season,
)
from championship.seasons.helpers import get_seasons_with_scores
from multisite.constants import SWISS_DOMAIN

scores_computation_time_seconds = Summary(
    "scores_computation_time_seconds", "Time spent to compute scores of all players"
)
scores_computation_results_count = Gauge(
    "scores_computation_results_count",
    "Number of ResultUsed for computing the leaderboard.",
    ["season_id", "season_name"],
)

SCOREMETHOD_PER_SEASON = {
    SEASON_2023: ScoreMethod2023,
    SEASON_2024: ScoreMethod2024,
    SEASON_2025: ScoreMethod2025,
    EU_SEASON_2025: ScoreMethodEu2025,
    EU_SEASON_2024_MOCKUP: ScoreMethodEu2025,
    INVITATIONAL_SPRING_2025: ScoreMethodInvitationalSpring2025,
    SWISS_SEASON_ALL: ScoreMethodAll,
}


def get_results_with_qps(
    event_player_results: models.QuerySet[Result],
) -> Iterable[tuple[Result, Any]]:
    """
    Pass a QuerySet of Result, and get it annotated with the following fields:
    - has_top8: True if the event has a top8
    - qps: the number of QPs the player got in this event
    - event_size: the number of players in the event
    - event: the event
    - byes: Number of byes awarded for this result.
    """
    results = event_player_results.select_related("event").annotate(
        event_size=Count("event__result"),
        top_count=Count("event__result__playoff_result"),
    )

    # Calculate the number of rounds by taking the sum of win/draw/loss. We
    # take the Max to account for players dropping early.
    rounds_per_event = {
        row["event"]: row["rounds"]
        for row in Result.objects.values("event").annotate(
            rounds=Max(F("win_count") + F("draw_count") + F("loss_count"))
        )
    }

    for result in results:
        method = SCOREMETHOD_PER_SEASON[result.event.season]
        result.has_top8 = result.top_count > 0
        score = method.score_for_result(  # type: ignore
            result,
            event_size=result.event_size,
            has_top8=result.has_top8,
            total_rounds=rounds_per_event[result.event_id],
        )
        yield result, score


def _score_cache_key(season, country_code=settings.DEFAULT_COUNTRY):
    if country_code and Site.objects.get_current().domain != SWISS_DOMAIN:
        return f"compute_scoresS{season.slug}C{country_code}"
    else:
        return f"compute_scoresS{season.slug}"


@cache_function(cache_key=_score_cache_key, cache_ttl=15 * 60)
@scores_computation_time_seconds.time()
def compute_scores(
    season: Season, country_code: str = settings.DEFAULT_COUNTRY
) -> dict[int, LeaderboardScore]:
    scores_by_player: dict[int, Any] = {}
    results = Result.objects.filter(
        event__date__gte=season.start_date,
        event__date__lte=season.end_date,
        player__in=Player.leaderboard_objects.all(),
    ).exclude(event__category=Event.Category.OTHER)

    if Site.objects.get_current().domain == SWISS_DOMAIN:
        results = results.on_site()
    else:
        results = results.filter(
            player__playerseasondata__country=country_code,
            player__playerseasondata__season_slug=season.slug,
        )

    count = 0
    for result, score in get_results_with_qps(results):
        if score:
            count += 1
            try:
                scores_by_player[result.player_id] += score
            except KeyError:
                scores_by_player[result.player_id] = score

    scores_computation_results_count.labels(season.slug, season.name).set(count)

    return SCOREMETHOD_PER_SEASON[season].finalize_scores(  # type: ignore
        scores_by_player,
        country_code,
    )


@receiver(post_delete, sender=Result)
@receiver(pre_save, sender=Result)
def invalidate_score_cache(sender, instance, **kwargs):
    for season in get_seasons_with_scores():
        if season.start_date <= instance.event.date <= season.end_date:
            if Site.objects.get_current().domain == SWISS_DOMAIN:
                cache.delete(_score_cache_key(season))
            else:
                player_season_data = PlayerSeasonData.objects.filter(
                    player_id=instance.player_id, season_slug=season.slug
                ).first()
                if player_season_data:
                    cache.delete(_score_cache_key(season, player_season_data.country))


def combine_scores_with_players(
    scores_by_player: dict[int, LeaderboardScore]
) -> list[Player]:
    """Returns a list of Player with their score.

    This function returns a list of Players with an additional score property
    (of type Score), containing all informations required to render a
    leaderboard.
    """
    players_with_score = []
    for player in Player.leaderboard_objects.all():
        if score := scores_by_player.get(player.id):
            player.score = score
            players_with_score.append(player)
    players_with_score.sort(key=lambda l: l.score.rank)
    return players_with_score


def get_leaderboard(
    season: Season, country_code: str = settings.DEFAULT_COUNTRY
) -> list[Player]:
    """Returns a list of Player with their score.

    This function returns a list of Players with an additional score property
    (of type Score), containing all informations required to render a
    leaderboard.
    """
    scores_by_player = compute_scores(season, country_code)
    return combine_scores_with_players(scores_by_player)


def _organizer_score_cache_key(l: OrganizerLeague):
    return f"compute_organizer_scores_o{l.organizer_id}s{l.start_date}e{l.end_date}f{l.format}c{l.category}p{l.playoffs}"


@cache_function(cache_key=_organizer_score_cache_key, cache_ttl=60 * 60)
def compute_organizer_scores(league: OrganizerLeague) -> dict[int, LeaderboardScore]:
    qps_by_player: dict[int, int] = {}
    for result, score in get_results_with_qps(league.get_results()):
        if score:
            try:
                qps_by_player[result.player_id] += score.qps
            except KeyError:
                qps_by_player[result.player_id] = score.qps

    sorted_qps = sorted(qps_by_player.items(), key=lambda x: x[1], reverse=True)
    scores = {
        player_id: LeaderboardScore(total_score=score, rank=i + 1)
        for i, (player_id, score) in enumerate(sorted_qps)
    }
    return scores


@receiver(post_delete, sender=Result)
@receiver(pre_save, sender=Result)
def invalidate_organizer_score_cache(sender, instance, **kwargs):
    for league in OrganizerLeague.objects.filter(
        organizer=instance.event.organizer,
        start_date__gte=instance.event.date,
        end_date__lte=instance.event.date,
    ):
        cache.delete(_organizer_score_cache_key(league))


def get_organizer_leaderboard(league: OrganizerLeague) -> list[Player]:
    """Returns a list of Player with their score.

    This function returns a list of Players with an additional score property
    (of type Score), containing all informations required to render a
    leaderboard.
    """
    scores_by_player = compute_organizer_scores(league)
    return combine_scores_with_players(scores_by_player)
