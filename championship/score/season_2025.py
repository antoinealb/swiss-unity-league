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
from dataclasses import dataclass

from championship.models import Event, Result, SpecialReward
from championship.score.types import LeaderboardScore, QualificationType
from championship.season import SEASON_2025


class ScoreMethod2025:
    @dataclass
    class Score:
        qps: int
        byes: int

        def __add__(self, o: "ScoreMethod2025.Score") -> "ScoreMethod2025.Score":
            return ScoreMethod2025.Score(qps=self.qps + o.qps, byes=self.byes + o.byes)

    MULT = {
        Event.Category.REGULAR: 1,
        Event.Category.REGIONAL: 4,
        Event.Category.PREMIER: 6,
    }
    PARTICIPATION_POINTS = 3
    POINTS_FOR_TOP = {
        Event.Category.PREMIER: {
            Result.PlayoffResult.WINNER: 400,
            Result.PlayoffResult.FINALIST: 240,
            Result.PlayoffResult.SEMI_FINALIST: 160,
            Result.PlayoffResult.QUARTER_FINALIST: 120,
        },
        Event.Category.REGIONAL: {
            Result.PlayoffResult.WINNER: 100,
            Result.PlayoffResult.FINALIST: 60,
            Result.PlayoffResult.SEMI_FINALIST: 40,
            Result.PlayoffResult.QUARTER_FINALIST: 30,
        },
        Event.Category.REGULAR: {
            Result.PlayoffResult.WINNER: 12,
            Result.PlayoffResult.FINALIST: 9,
            Result.PlayoffResult.SEMI_FINALIST: 6,
            Result.PlayoffResult.QUARTER_FINALIST: 3,
        },
    }
    POINTS_FOR_MATCHPOINT_RATE = [
        (
            0.7,
            {
                Event.Category.PREMIER: 60,
                Event.Category.REGIONAL: 20,
                Event.Category.REGULAR: 0,
            },
        ),
        (
            0.65,
            {
                Event.Category.PREMIER: 30,
                Event.Category.REGIONAL: 10,
                Event.Category.REGULAR: 0,
            },
        ),
    ]
    LEADERBOARD_QUALIFICATION_RANK = 36
    DIRECT_QUALIFICATION_REASON = (
        "Direct qualification for {ranking} place at '{event_name}'"
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
        points = result.points + cls.PARTICIPATION_POINTS
        points = points * cls.MULT[category]
        if result.playoff_result:
            points += cls.POINTS_FOR_TOP[category][result.playoff_result]
        elif has_top_8:
            # If the event has a top 8, but the player didn't make it, they can
            # still get extra points if their match point rate (mpr) is higher than the
            # threshold of 70% or 65%.
            maximum_match_points = 3.0 * total_rounds
            for mpr_threshold, points_for_mpr in cls.POINTS_FOR_MATCHPOINT_RATE:
                players_mpr = result.points / maximum_match_points
                if players_mpr >= mpr_threshold:
                    points += points_for_mpr[category]
                    break
        return points

    @classmethod
    def _byes_for_rank(cls, rank: int) -> int:
        if rank <= 4:
            return 1
        else:
            return 0

    MAX_BYES = 1

    @classmethod
    def finalize_scores(
        cls,
        scores_by_player: dict[int, Score],
    ) -> dict[int, LeaderboardScore]:
        """Implements the last step of score processing.

        This function takes a dictionary of player_id to Score mappings and turns it
        into a dictionary of player_id to LeaderboardScore mappings, checking the maximum number of byes
        and deciding who is qualified and not.

        Returns a dictionary of player_id to LeaderboardScore.

        """
        premier_events = (
            Event.objects.filter(
                category=Event.Category.PREMIER,
                date__gte=SEASON_2025.start_date,
                date__lte=SEASON_2025.end_date,
            )
            .prefetch_related("result_set")
            .order_by("date")
        )
        direct_qualification_reasons_by_player = {}
        rewards = SpecialReward.objects.filter(
            result__event__date__gte=SEASON_2025.start_date,
            result__event__date__lte=SEASON_2025.end_date,
        ).all()
        for reward in rewards:
            if reward.direct_invite:
                direct_qualification_reasons_by_player[reward.result.player_id] = (
                    cls.DIRECT_QUALIFICATION_REASON.format(
                        ranking=reward.result.get_ranking_display(),
                        event_name=reward.result.event.name,
                    )
                )
        for premier_event in premier_events:
            for result in sorted(premier_event.result_set.all()):
                if result.player_id not in direct_qualification_reasons_by_player:
                    direct_qualification_reasons_by_player[result.player_id] = (
                        cls.DIRECT_QUALIFICATION_REASON.format(
                            ranking=result.get_ranking_display(),
                            event_name=premier_event.name,
                        )
                    )
                    break

        if SEASON_2025.can_enter_results(datetime.date.today()):
            leaderboard_reason = "This place qualifies for the SUL Championship tournament at the end of the Season"
        else:
            leaderboard_reason = "Qualified for SUL Championship tournament"

        sorted_scores = sorted(
            scores_by_player.items(), key=lambda x: x[1].qps, reverse=True
        )
        scores = {}
        for i, (player_id, score) in enumerate(sorted_scores):
            rank = i + 1
            byes = (
                cls._byes_for_rank(rank)
                + score.byes
                + sum([r.byes for r in rewards if r.result.player_id == player_id])
            )
            byes = min(byes, cls.MAX_BYES)

            scores[player_id] = LeaderboardScore(
                total_score=score.qps,
                rank=rank,
                byes=byes,
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
    def score_for_result(cls, result, event_size, has_top8, total_rounds) -> Score:
        qps = cls._qps_for_result(result, event_size, has_top8, total_rounds)
        return cls.Score(qps=qps, byes=0)
