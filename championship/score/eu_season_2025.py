# Copyright 2025 Leonin League
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
import math
from dataclasses import dataclass

from django.db.models import Count

from championship.models import Event, Result
from championship.score.types import LeaderboardScore, QualificationType
from championship.seasons.definitions import EU_SEASON_2025


class ScoreMethodEu2025:
    @dataclass
    class Score:
        qps: int

        def __add__(self, o: "ScoreMethodEu2025.Score") -> "ScoreMethodEu2025.Score":
            return ScoreMethodEu2025.Score(qps=self.qps + o.qps)

    @dataclass
    class ExtraWinForLargeEvents:
        rank_required: int
        rounds_required: int

    MULT = {
        Event.Category.REGULAR: 1,
        Event.Category.REGIONAL: 4,
        Event.Category.PREMIER: 4,
        Event.Category.NATIONAL: 5,  # Included for sake of completeness, but there shouldn't be any nationals this year
        Event.Category.QUALIFIER: 6,
        Event.Category.GRAND_PRIX: 7,
    }
    PARTICIPATION_POINTS = 3
    POINTS_PER_WIN = 3
    WIN_EQUIVALENT_FOR_PLAYOFFS = {
        Result.PlayoffResult.WINNER: 15,
        Result.PlayoffResult.FINALIST: 9,
        Result.PlayoffResult.SEMI_FINALIST: 6,
        Result.PlayoffResult.QUARTER_FINALIST: 4,
    }
    EXTRA_WINS = [
        ExtraWinForLargeEvents(rank_required=16, rounds_required=6),
        ExtraWinForLargeEvents(rank_required=32, rounds_required=8),
        ExtraWinForLargeEvents(rank_required=64, rounds_required=10),
    ]
    LEADERBOARD_QUALIFICATION_RANK = 40
    DIRECT_QUALIFICATION_REASON = (
        "Direct invite to European Magic Cup for {ranking} place at '{event_name}'"
    )

    @classmethod
    def _qps_for_result(
        cls,
        result: Result,
        event_size: int,
        has_top_8: bool,
        total_rounds: int,
    ) -> int:
        """
        Returns how many QPs a player got in a single event.
        """
        category = result.event.category
        multiplier = cls.MULT[category]

        if result.points:
            swiss_points = (result.points + cls.PARTICIPATION_POINTS) * multiplier
        else:
            swiss_points = 0

        if has_top_8:
            estimated_rounds = math.ceil(math.log2(event_size))
            win_equivalent_for_playoff = cls.WIN_EQUIVALENT_FOR_PLAYOFFS.get(
                result.playoff_result, 0
            )
            extra_wins_for_large_event = 0
            for extra_wins in cls.EXTRA_WINS:
                if (
                    result.ranking <= extra_wins.rank_required
                    and estimated_rounds >= extra_wins.rounds_required
                ):
                    extra_wins_for_large_event += 1

            playoff_points = (
                (win_equivalent_for_playoff + extra_wins_for_large_event)
                * multiplier
                * cls.POINTS_PER_WIN
            )
        else:
            playoff_points = 0

        return max(swiss_points, playoff_points)

    @classmethod
    def finalize_scores(
        cls,
        scores_by_player: dict[int, Score],
    ) -> dict[int, LeaderboardScore]:
        """Implements the last step of score processing.

        This function takes a dictionary of player_id to Score mappings and turns it
        into a dictionary of player_id to LeaderboardScore mappings, deciding who is qualified and not.

        Returns a dictionary of player_id to LeaderboardScore.

        """
        qualifier_event = (
            Event.objects.filter(
                category=Event.Category.QUALIFIER,
                date__gte=EU_SEASON_2025.start_date,
                date__lte=EU_SEASON_2025.end_date,
            )
            .prefetch_related("result_set")
            .order_by("date")
            .annotate(top_count=Count("result__playoff_result"))
            .filter(top_count__gt=0)
        )
        direct_qualification_reasons_by_player = {}
        for qualifier_event in qualifier_event:
            for result in sorted(qualifier_event.result_set.all()):
                if result.player_id not in direct_qualification_reasons_by_player:
                    direct_qualification_reasons_by_player[result.player_id] = (
                        cls.DIRECT_QUALIFICATION_REASON.format(
                            ranking=result.get_ranking_display(),
                            event_name=qualifier_event.name,
                        )
                    )
                    break

        if EU_SEASON_2025.can_enter_results(datetime.date.today()):
            leaderboard_reason = "This place qualifies for the National Championship at the end of the Season"
        else:
            leaderboard_reason = "Qualified for National Championship"

        sorted_scores = sorted(
            scores_by_player.items(), key=lambda x: x[1].qps, reverse=True
        )
        scores = {}
        for i, (player_id, score) in enumerate(sorted_scores):
            rank = i + 1

            scores[player_id] = LeaderboardScore(
                total_score=score.qps,
                rank=rank,
                byes=0,
            )
            if player_id in direct_qualification_reasons_by_player:
                scores[player_id].qualification_type = QualificationType.DIRECT
                scores[player_id].qualification_reason = (
                    direct_qualification_reasons_by_player[player_id]
                )
            elif rank <= cls.LEADERBOARD_QUALIFICATION_RANK:
                scores[player_id].qualification_type = QualificationType.LEADERBOARD
                scores[player_id].qualification_reason = leaderboard_reason

        return scores

    @classmethod
    def score_for_result(
        cls, result, event_size, has_top8, total_rounds
    ) -> Score | None:
        if result.event.category in [Event.Category.NATIONAL, Event.Category.OTHER]:
            return None
        qps = cls._qps_for_result(result, event_size, has_top8, total_rounds)
        return cls.Score(qps=qps)