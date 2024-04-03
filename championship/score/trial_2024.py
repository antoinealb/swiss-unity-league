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

from championship.models import Count, Event
from championship.score.season_2024 import ScoreMethod2024
from championship.score.types import LeaderboardScore, QualificationType
from championship.season import SEASON_2024, SUL_TRIAL_2024


class ScoreMethodTrial2024(ScoreMethod2024):
    TOTAL_QUALIFICATION_SLOTS = 80

    @classmethod
    def finalize_scores(
        cls,
        scores_by_player: dict[int, ScoreMethod2024.Score],
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
        for i, (player_id, score) in enumerate(sorted_scores):
            rank = i + 1

            scores[player_id] = LeaderboardScore(
                total_score=score.qps,
                rank=rank,
            )
            if i < cls.TOTAL_QUALIFICATION_SLOTS:
                scores[player_id].qualification_type = QualificationType.LEADERBOARD
                scores[player_id].qualification_reason = "Qualified for SUL Trial 2024"

        return scores
