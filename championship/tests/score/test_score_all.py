from django.test import TestCase

from championship.factories import EventFactory, EventPlayerResultFactory, PlayerFactory
from championship.models import Event
from championship.score.generic import compute_scores
from championship.season import SEASON_ALL, SEASONS_WITH_RANKING


class TestComputeScoreFor2023(TestCase):
    def compute_scores(self):
        return compute_scores(SEASON_ALL)

    def test_score_all(self):
        player = PlayerFactory()
        for season in SEASONS_WITH_RANKING:
            event = EventFactory(
                date=season.start_date, category=Event.Category.REGULAR
            )
            EventPlayerResultFactory(event=event, player=player, points=3)

        scores = self.compute_scores()
        self.assertEqual(scores[player.id].total_score, 6 * len(SEASONS_WITH_RANKING))
