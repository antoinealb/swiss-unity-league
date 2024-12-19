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

from dataclasses import dataclass

from championship.models import Event, Result
from championship.score.types import LeaderboardScore, QualificationType


class ScoreMethod2023:
    @dataclass
    class Score:
        qps: int
        byes: int

        def __add__(self, o: "ScoreMethod2023.Score") -> "ScoreMethod2023.Score":
            return ScoreMethod2023.Score(qps=self.qps + o.qps, byes=self.byes + o.byes)

    MULT = {
        Event.Category.REGULAR: 1,
        Event.Category.REGIONAL: 4,
        Event.Category.PREMIER: 6,
    }
    PARTICIPATION_POINTS = 3
    POINTS_FOR_TOP = {
        Event.Category.PREMIER: {
            Result.PlayoffResult.WINNER: 500,
            Result.PlayoffResult.FINALIST: 300,
            Result.PlayoffResult.SEMI_FINALIST: 200,
            Result.PlayoffResult.QUARTER_FINALIST: 150,
        },
        Event.Category.REGIONAL: {
            Result.PlayoffResult.WINNER: 100,
            Result.PlayoffResult.FINALIST: 60,
            Result.PlayoffResult.SEMI_FINALIST: 40,
            Result.PlayoffResult.QUARTER_FINALIST: 30,
        },
    }
    POINTS_TOP_9_12 = {
        Event.Category.PREMIER: 75,
        Event.Category.REGIONAL: 15,
        Event.Category.REGULAR: 0,
    }
    POINTS_TOP_13_16 = {
        Event.Category.PREMIER: 50,
        Event.Category.REGIONAL: 10,
        Event.Category.REGULAR: 0,
    }

    @classmethod
    def _qps_for_result(
        cls,
        result: Result,
        event_size: int,
        has_top_8: bool,
    ) -> int:
        """
        Returns how many QPs a player got in a single event.
        """
        category = result.event.category
        points = result.points + cls.PARTICIPATION_POINTS
        points = points * cls.MULT[category]

        if category not in cls.POINTS_FOR_TOP:
            return points

        if result.playoff_result:
            points += cls.POINTS_FOR_TOP[category][result.playoff_result]
        elif has_top_8:
            # For large tournaments, we award points for placing, even outside of
            # top8. See the rules for explanation
            if event_size > 32 and 9 <= result.ranking <= 12:
                points += cls.POINTS_TOP_9_12[category]
            elif event_size > 48 and 13 <= result.ranking <= 16:
                points += cls.POINTS_TOP_13_16[category]
            elif result.ranking <= 8:
                # If we are in this case, it means the event did not play a top8,
                # only a top4, and we still need to award points for 5th-8th.
                points += cls.POINTS_FOR_TOP[category][
                    Result.PlayoffResult.QUARTER_FINALIST
                ]

        return points

    @classmethod
    def _byes_for_result(
        cls,
        result: Result,
        event_size: int,
        has_top_8: bool,
    ) -> int:
        """Returns how many byes a given result gives."""
        MIN_SIZE_EXTRA_BYE = 128
        if (
            result.event_size > MIN_SIZE_EXTRA_BYE
            and result.event.category == Event.Category.PREMIER
            and result.playoff_result == Result.PlayoffResult.WINNER
        ):
            return 2
        return 0

    @classmethod
    def _byes_for_rank(cls, rank: int) -> int:
        if rank <= 1:
            return 2
        elif rank <= 5:
            return 1
        else:
            return 0

    MAX_BYES = 2

    @classmethod
    def finalize_scores(
        cls, scores_by_player: dict[int, Score], country_code: str
    ) -> dict[int, LeaderboardScore]:
        """Implements the last step of score processing.

        This function takes a list of (player_id, score) tuples and turns it
        into a sequence of Score objects, checking the maximum number of byes
        and deciding who is qualified and not.

        Returns a dict of (player_id: Score)

        """
        sorted_scores = sorted(
            scores_by_player.items(), key=lambda x: x[1].qps, reverse=True
        )
        scores = {}
        for i, (player, score) in enumerate(sorted_scores):
            rank = i + 1
            byes = cls._byes_for_rank(rank) + score.byes
            byes = min(byes, cls.MAX_BYES)

            scores[player] = LeaderboardScore(
                total_score=score.qps,
                rank=rank,
                byes=byes,
            )
            if rank <= 40:
                scores[player].qualification_type = QualificationType.LEADERBOARD
                scores[player].qualification_reason = (
                    "Qualified for the SUL Invitational tournament"
                )

        return scores

    @classmethod
    def score_for_result(
        cls, result, event_size, has_top8, total_rounds
    ) -> Score | None:
        if result.event.category not in [
            Event.Category.REGULAR,
            Event.Category.REGIONAL,
            Event.Category.PREMIER,
        ]:
            return None
        qps = cls._qps_for_result(result, event_size, has_top8)
        byes = cls._byes_for_result(result, event_size, has_top8)
        return cls.Score(qps=qps, byes=byes)
