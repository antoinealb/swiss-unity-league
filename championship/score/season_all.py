from dataclasses import dataclass
from typing import Any
from championship.models import Event, EventPlayerResult
from championship.score.types import LeaderboardScore


class ScoreMethodAll:
    @classmethod
    def finalize_scores(
        cls, scores_by_player: dict[int, Any]
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

            scores[player] = LeaderboardScore(total_score=score.qps, rank=rank)

        return scores
