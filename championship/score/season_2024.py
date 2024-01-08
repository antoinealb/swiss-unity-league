from dataclasses import dataclass
from championship.models import Event, EventPlayerResult
from championship.score.types import LeaderboardScore


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
            EventPlayerResult.SingleEliminationResult.WINNER: 400,
            EventPlayerResult.SingleEliminationResult.FINALIST: 240,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST: 160,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST: 120,
        },
        Event.Category.REGIONAL: {
            EventPlayerResult.SingleEliminationResult.WINNER: 100,
            EventPlayerResult.SingleEliminationResult.FINALIST: 60,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST: 40,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST: 30,
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

    @classmethod
    def _qps_for_result(
        cls,
        result: EventPlayerResult,
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
        result: EventPlayerResult,
        event_size: int,
        has_top_8: bool,
    ) -> int:
        """Returns how many byes a given result gives."""
        MIN_SIZE_EXTRA_BYE = 128
        if (
            result.event_size > MIN_SIZE_EXTRA_BYE
            and result.event.category == Event.Category.PREMIER
            and result.single_elimination_result
            == EventPlayerResult.SingleEliminationResult.WINNER
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
        cls, scores_by_player: dict[int, Score]
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
                qualified=rank <= 40,
            )

        return scores

    @classmethod
    def score_for_result(cls, result, event_size, has_top8, total_rounds) -> Score:
        qps = cls._qps_for_result(result, event_size, has_top8, total_rounds)
        byes = cls._byes_for_result(result, event_size, has_top8)
        return cls.Score(qps=qps, byes=byes)
