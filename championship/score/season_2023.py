from championship.models import Event, EventPlayerResult
from championship.score.types import Score


class ScoreMethod2023:
    MULT = {
        Event.Category.REGULAR: 1,
        Event.Category.REGIONAL: 4,
        Event.Category.PREMIER: 6,
    }
    PARTICIPATION_POINTS = 3
    POINTS_FOR_TOP = {
        Event.Category.PREMIER: {
            EventPlayerResult.SingleEliminationResult.WINNER: 500,
            EventPlayerResult.SingleEliminationResult.FINALIST: 300,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST: 200,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST: 150,
        },
        Event.Category.REGIONAL: {
            EventPlayerResult.SingleEliminationResult.WINNER: 100,
            EventPlayerResult.SingleEliminationResult.FINALIST: 60,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST: 40,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST: 30,
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
    def qps_for_result(
        cls,
        result: EventPlayerResult,
        event_size: int,
        has_top_8: bool,
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
                    EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST
                ]

        return points

    @classmethod
    def byes_for_result(
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
        cls, scores_by_player: dict[int, int], byes_per_player: dict[int, int]
    ) -> dict[int, Score]:
        """Implements the last step of score processing.

        This function takes a list of (player_id, score) tuples and turns it
        into a sequence of Score objects, checking the maximum number of byes
        and deciding who is qualified and not.

        Returns a dict of (player_id: Score)

        """
        sorted_scores = sorted(
            scores_by_player.items(), key=lambda x: x[1], reverse=True
        )
        scores = {}
        for i, (player, points) in enumerate(sorted_scores):
            rank = i + 1
            byes = cls._byes_for_rank(rank) + byes_per_player[player]
            byes = min(byes, cls.MAX_BYES)

            scores[player] = Score(
                total_score=points,
                rank=rank,
                byes=byes,
                qualified=rank <= 40,
            )

        return scores
