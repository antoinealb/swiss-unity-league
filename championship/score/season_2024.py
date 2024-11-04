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
from dataclasses import dataclass

from championship.models import Count, Event, Result, SpecialReward
from championship.score.types import LeaderboardScore, QualificationType
from championship.season import SEASON_2024


class ScoreMethod2024:
    @dataclass
    class Score:
        qps: int
        byes: int

        def __add__(self, o: "ScoreMethod2024.Score") -> "ScoreMethod2024.Score":
            return ScoreMethod2024.Score(qps=self.qps + o.qps, byes=self.byes + o.byes)

    MULT = {
        Event.Category.REGULAR: 1,
        Event.Category.REGIONAL: 4,
        Event.Category.PREMIER: 6,
    }
    PARTICIPATION_POINTS = 3
    POINTS_FOR_TOP = {
        Event.Category.PREMIER: {
            Result.SingleEliminationResult.WINNER: 400,
            Result.SingleEliminationResult.FINALIST: 240,
            Result.SingleEliminationResult.SEMI_FINALIST: 160,
            Result.SingleEliminationResult.QUARTER_FINALIST: 120,
        },
        Event.Category.REGIONAL: {
            Result.SingleEliminationResult.WINNER: 100,
            Result.SingleEliminationResult.FINALIST: 60,
            Result.SingleEliminationResult.SEMI_FINALIST: 40,
            Result.SingleEliminationResult.QUARTER_FINALIST: 30,
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
    TOTAL_QUALIFICATION_SLOTS = 40
    MIN_PLAYERS_FOR_DIRECT_QUALIFICATION = 40
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
        if category in cls.POINTS_FOR_TOP:
            if result.single_elimination_result:
                points += cls.POINTS_FOR_TOP[category][result.single_elimination_result]
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
    def _byes_for_result(
        cls,
        result: Result,
        event_size: int,
        has_top_8: bool,
    ) -> int:
        """Returns how many byes a given result gives."""
        return 0

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

        This function takes a list of (player_id, score) tuples and turns it
        into a sequence of Score objects, checking the maximum number of byes
        and deciding who is qualified and not.

        Returns a dict of (player_id: Score)

        """
        # Premier events with 40 or more players award a direct qualification to the winner of the event.
        # If that player is already qualified, then the invite is passed to the next player in the standings of the event.
        events = (
            Event.objects.filter(
                category=Event.Category.PREMIER,
                date__gte=SEASON_2024.start_date,
                date__lte=SEASON_2024.end_date,
            )
            .annotate(result_cnt=Count("result"))
            .filter(result_cnt__gte=cls.MIN_PLAYERS_FOR_DIRECT_QUALIFICATION)
            .prefetch_related("result_set")
            .order_by("date")
        )
        direct_qualification_reasons_by_player = {}
        for event in events:
            for result in sorted(event.result_set.all()):
                if result.player_id not in direct_qualification_reasons_by_player:
                    direct_qualification_reasons_by_player[result.player_id] = (
                        cls.DIRECT_QUALIFICATION_REASON.format(
                            ranking=result.get_ranking_display(), event_name=event.name
                        )
                    )
                    break

        rewards = SpecialReward.objects.filter(
            result__event__date__gte=SEASON_2024.start_date,
            result__event__date__lte=SEASON_2024.end_date,
        ).select_related("result", "result__event")
        for reward in rewards:
            if reward.direct_invite:
                direct_qualification_reasons_by_player[reward.result.player_id] = (
                    cls.DIRECT_QUALIFICATION_REASON.format(
                        ranking=reward.result.get_ranking_display(),
                        event_name=reward.result.event.name,
                    )
                )

        if SEASON_2024.can_enter_results(datetime.date.today()):
            leaderboard_reason = "This place qualifies for the SUL Invitational tournament at the end of the Season"
        else:
            leaderboard_reason = "Qualified for SUL Invitational tournament"

        num_leaderboard_qualifications = cls.TOTAL_QUALIFICATION_SLOTS - len(
            direct_qualification_reasons_by_player
        )
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
            elif num_leaderboard_qualifications > 0:
                scores[player_id].qualification_type = QualificationType.LEADERBOARD
                scores[player_id].qualification_reason = leaderboard_reason
                num_leaderboard_qualifications -= 1

        return scores

    @classmethod
    def score_for_result(cls, result, event_size, has_top8, total_rounds) -> Score:
        qps = cls._qps_for_result(result, event_size, has_top8, total_rounds)
        byes = cls._byes_for_result(result, event_size, has_top8)
        return cls.Score(qps=qps, byes=byes)
