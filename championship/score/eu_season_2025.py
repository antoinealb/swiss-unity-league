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

from championship.models import Event, NationalLeaderboard, Result
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
        Event.Category.REGIONAL: 3,
        Event.Category.PREMIER: 3,
        Event.Category.NATIONAL: 4,
        Event.Category.QUALIFIER: 5,
        Event.Category.GRAND_PRIX: 6,
    }
    PARTICIPATION_POINTS = 3
    POINTS_PER_WIN = 3
    WIN_EQUIVALENT_FOR_PLAYOFFS = {
        Result.PlayoffResult.WINNER: 16,
        Result.PlayoffResult.FINALIST: 10,
        Result.PlayoffResult.SEMI_FINALIST: 7,
        Result.PlayoffResult.QUARTER_FINALIST: 5,
    }
    EXTRA_WINS = [
        ExtraWinForLargeEvents(rank_required=12, rounds_required=6),
        ExtraWinForLargeEvents(rank_required=16, rounds_required=7),
        ExtraWinForLargeEvents(rank_required=32, rounds_required=8),
        ExtraWinForLargeEvents(rank_required=64, rounds_required=9),
        ExtraWinForLargeEvents(rank_required=128, rounds_required=10),
    ]
    LEADERBOARD_QUALIFICATION_RANK = 40
    SEASON = EU_SEASON_2025

    @classmethod
    def _estimated_rounds(cls, event_size: int) -> int:
        return math.ceil(math.log2(event_size))

    @classmethod
    def _win_equivalent_for_rank(
        cls,
        result: Result,
        event_size: int,
    ):
        win_equivalent_for_playoff = cls.WIN_EQUIVALENT_FOR_PLAYOFFS.get(
            result.playoff_result, 0
        )
        extra_wins_for_large_event = 0
        for extra_wins in cls.EXTRA_WINS:
            if (
                result.ranking <= extra_wins.rank_required
                and cls._estimated_rounds(event_size) >= extra_wins.rounds_required
            ):
                extra_wins_for_large_event += 1

        return win_equivalent_for_playoff + extra_wins_for_large_event

    @classmethod
    def _qps_for_result(
        cls,
        result: Result,
        event_size: int,
        has_top_8: bool,
        total_rounds: int,
    ) -> int | None:
        """
        Returns how many QPs a player got in a single event.
        """
        multiplier = cls.MULT[result.event.category]
        # if result.event.category == Event.Category.REGIONAL and not has_top_8:
        #     multiplier = 1
        points = []
        if result.points is not None:
            swiss_points = (result.points + cls.PARTICIPATION_POINTS) * multiplier
            points.append(swiss_points)

        if has_top_8:
            win_equivalent_for_rank = cls._win_equivalent_for_rank(result, event_size)
            if win_equivalent_for_rank > 0:
                estimated_swiss_wins = cls._estimated_rounds(event_size) - 1
                match_point_equivalent = (
                    win_equivalent_for_rank + estimated_swiss_wins
                ) * cls.POINTS_PER_WIN

                top_finish_points = (
                    match_point_equivalent + cls.PARTICIPATION_POINTS
                ) * multiplier
                points.append(top_finish_points)

        return None if not points else max(points)

    @classmethod
    def finalize_scores(
        cls, scores_by_player: dict[int, Score], country_code: str
    ) -> dict[int, LeaderboardScore]:
        """Implements the last step of score processing.

        This function takes a dictionary of player_id to Score mappings and turns it
        into a dictionary of player_id to LeaderboardScore mappings, deciding who is qualified and not.

        Returns a dictionary of player_id to LeaderboardScore.

        """
        qualifier_event = (
            Event.objects.filter(
                category=Event.Category.QUALIFIER,
                date__gte=cls.SEASON.start_date,
                date__lte=cls.SEASON.end_date,
            )
            .prefetch_related("result_set")
            .order_by("date")
            .annotate(top_count=Count("result__playoff_result"))
            .filter(top_count__gt=0)
        )
        national_leaderboard = NationalLeaderboard.objects.filter(
            country=country_code, season_slug=cls.SEASON.slug
        ).first()
        direct_qualification_reasons_by_player = {}
        for qualifier_event in qualifier_event:
            for result in sorted(qualifier_event.result_set.all()):
                if result.player_id not in direct_qualification_reasons_by_player:
                    direct_qualification_reasons_by_player[result.player_id] = (
                        f"Invite to European Magic Cup for {result.get_ranking_display()} place at '{qualifier_event.name}'"
                    )
                    break

        if cls.SEASON.can_enter_results(datetime.date.today()):
            leaderboard_reason = "This place qualifies for the National Championship at the end of the season"
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
            elif (
                national_leaderboard
                and rank <= national_leaderboard.continental_invites
            ):
                scores[player_id].qualification_type = QualificationType.DIRECT
                scores[player_id].qualification_reason = (
                    "Invite to European Magic Cup at the end of the season"
                )
            elif national_leaderboard and rank <= national_leaderboard.national_invites:
                scores[player_id].qualification_type = QualificationType.LEADERBOARD
                scores[player_id].qualification_reason = leaderboard_reason

        return scores

    @classmethod
    def score_for_result(
        cls, result, event_size, has_top8, total_rounds
    ) -> Score | None:
        if result.event.category != Event.Category.OTHER:
            qps = cls._qps_for_result(result, event_size, has_top8, total_rounds)
            if qps is not None:
                return cls.Score(qps=qps)
        return None
