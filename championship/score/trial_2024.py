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

        num_leaderboard_qualifications = cls.TOTAL_QUALIFICATION_SLOTS
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
            if num_leaderboard_qualifications > 0:
                scores[player_id].qualification_type = QualificationType.LEADERBOARD
                scores[player_id].qualification_reason = "Qualified for SUL Trial 2024"
                num_leaderboard_qualifications -= 1

        return scores
