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

from django.test import TestCase

from championship.factories import Event2024Factory, PlayerFactory, ResultFactory
from championship.models import Event, Result
from championship.score import compute_scores
from championship.score.trial_2024 import ScoreMethodTrial2024
from championship.score.types import QualificationType
from championship.season import SUL_TRIAL_2024


class TestScoresOutOfTrialSeason(TestCase):

    def compute_scores(self):
        return compute_scores(SUL_TRIAL_2024)

    def test_events_out_of_season_dont_contribute_score(self):
        event = Event2024Factory(
            date=SUL_TRIAL_2024.start_date - datetime.timedelta(days=1)
        )
        ResultFactory(event=event)
        event = Event2024Factory(
            date=SUL_TRIAL_2024.end_date + datetime.timedelta(days=1)
        )
        ResultFactory(event=event)
        got_scores = self.compute_scores()
        self.assertEqual({}, got_scores)

    def test_events_in_season_contribute_score(self):
        event = Event2024Factory(date=SUL_TRIAL_2024.start_date)
        ResultFactory(event=event)
        event = Event2024Factory(date=SUL_TRIAL_2024.end_date)
        ResultFactory(event=event)
        got_scores = self.compute_scores()
        self.assertEqual(2, len(got_scores))


def create_test_tournament(players, category=Event.Category.PREMIER, with_top8=True):
    event = Event2024Factory(category=category, date=SUL_TRIAL_2024.start_date)
    num_players = len(players)
    for i, player in enumerate(players):
        rank = i + 1

        if category != Event.Category.REGULAR and with_top8:
            if rank == 1:
                playoff_result = Result.PlayoffResult.WINNER
            elif rank == 2:
                playoff_result = Result.PlayoffResult.FINALIST
            elif rank <= 4:
                playoff_result = Result.PlayoffResult.SEMI_FINALIST
            elif rank <= 8:
                playoff_result = Result.PlayoffResult.QUARTER_FINALIST
            else:
                playoff_result = None

        ResultFactory(
            player=player,
            points=num_players - i,
            ranking=rank,
            playoff_result=playoff_result,
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
