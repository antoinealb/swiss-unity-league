import datetime

from django.test import TestCase

from championship.factories import *
from championship.models import *
from championship.score import compute_scores
from championship.score.trial_2024 import ScoreMethodTrial2024
from championship.score.types import QualificationType
from championship.season import SEASON_2024, SUL_TRIAL_2024


class TestScoresOutOfTrialSeason(TestCase):

    def compute_scores(self):
        return compute_scores(SUL_TRIAL_2024)

    def test_events_out_of_season_dont_contribute_score(self):
        event = Event2024Factory(
            date=SUL_TRIAL_2024.start_date - datetime.timedelta(days=1)
        )
        EventPlayerResultFactory(event=event)
        event = Event2024Factory(
            date=SUL_TRIAL_2024.end_date + datetime.timedelta(days=1)
        )
        EventPlayerResultFactory(event=event)
        got_scores = self.compute_scores()
        self.assertEqual({}, got_scores)

    def test_events_in_season_contribute_score(self):
        event = Event2024Factory(date=SUL_TRIAL_2024.start_date)
        EventPlayerResultFactory(event=event)
        event = Event2024Factory(date=SUL_TRIAL_2024.end_date)
        EventPlayerResultFactory(event=event)
        got_scores = self.compute_scores()
        self.assertEqual(2, len(got_scores))


def create_test_tournament(players, category=Event.Category.PREMIER, with_top8=True):
    event = Event2024Factory(category=category, date=SUL_TRIAL_2024.start_date)
    num_players = len(players)
    for i, player in enumerate(players):
        rank = i + 1

        if category != Event.Category.REGULAR and with_top8:
            if rank == 1:
                ser = EventPlayerResult.SingleEliminationResult.WINNER
            elif rank == 2:
                ser = EventPlayerResult.SingleEliminationResult.FINALIST
            elif rank <= 4:
                ser = EventPlayerResult.SingleEliminationResult.SEMI_FINALIST
            elif rank <= 8:
                ser = EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST
            else:
                ser = None

        EventPlayerResultFactory(
            player=player,
            points=num_players - i,
            ranking=rank,
            single_elimination_result=ser,
            event=event,
        )
    return event


class TestScoresQualified(TestCase):
    def setUp(self):
        self.num_qualified = ScoreMethodTrial2024.TOTAL_QUALIFICATION_SLOTS

    def compute_scores(self):
        return compute_scores(SUL_TRIAL_2024)

    def test_top_leaderboard_qualified(self):
        num_players = 100
        players = [PlayerFactory() for _ in range(num_players)]

        create_test_tournament(players, category=Event.Category.PREMIER)
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = [QualificationType.LEADERBOARD] * (self.num_qualified) + [
            QualificationType.NONE
        ] * (num_players - self.num_qualified)
        self.assertEqual(want_qualified, got_qualified)

    def test_top_leaderboard_no_byes(self):
        num_players = 100
        players = [PlayerFactory() for _ in range(num_players)]

        create_test_tournament(players, category=Event.Category.PREMIER)
        got_scores = self.compute_scores()
        got_byes = [s.byes for s in got_scores.values()]
        self.assertEqual([0] * num_players, got_byes)
