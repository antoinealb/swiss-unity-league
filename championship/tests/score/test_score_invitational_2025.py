# Copyright 2025 Leonin League
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

from championship.factories import Event2025Factory, ResultFactory
from championship.models import Event
from championship.score import compute_scores
from championship.score.invitational_spring_2025 import (
    ScoreMethodInvitationalSpring2025,
)
from championship.score.types import QualificationType
from championship.seasons.definitions import INVITATIONAL_SPRING_2025


class TestScoresOutOfTrialSeason(TestCase):

    def compute_scores(self):
        return compute_scores(INVITATIONAL_SPRING_2025)

    def test_events_out_of_season_dont_contribute_score(self):
        ResultFactory(
            event__date=INVITATIONAL_SPRING_2025.start_date - datetime.timedelta(days=1)
        )
        ResultFactory(
            event__date=INVITATIONAL_SPRING_2025.end_date + datetime.timedelta(days=1)
        )
        got_scores = self.compute_scores()
        self.assertEqual({}, got_scores)

    def test_events_in_season_contribute_score(self):
        ResultFactory(
            event__date=INVITATIONAL_SPRING_2025.start_date,
            event__category=Event.Category.REGULAR,
        )
        ResultFactory(
            event__date=INVITATIONAL_SPRING_2025.end_date,
            event__category=Event.Category.REGULAR,
        )
        got_scores = self.compute_scores()
        self.assertEqual(2, len(got_scores))


class TestScoresQualified(TestCase):
    def setUp(self):
        self.num_qualified = (
            ScoreMethodInvitationalSpring2025.LEADERBOARD_QUALIFICATION_RANK
        )

    def compute_scores(self):
        return compute_scores(INVITATIONAL_SPRING_2025)

    def test_premier_event_awards_two_direct_invites(self):
        num_players = 100
        Event2025Factory(
            players=num_players,
            category=Event.Category.PREMIER,
            date=INVITATIONAL_SPRING_2025.start_date,
            with_tops=8,
        )
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = (
            [QualificationType.DIRECT] * 2
            + [QualificationType.LEADERBOARD] * (self.num_qualified - 2)
            + [QualificationType.NONE] * (num_players - self.num_qualified)
        )
        self.assertEqual(want_qualified, got_qualified)

    def test_regional_with_tops_awards_one_direct_invite(self):
        num_players = 24
        Event2025Factory(
            players=num_players,
            category=Event.Category.REGIONAL,
            date=INVITATIONAL_SPRING_2025.start_date,
            with_tops=4,
        )
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = [QualificationType.DIRECT] * 1 + [
            QualificationType.LEADERBOARD
        ] * (num_players - 1)
        self.assertEqual(want_qualified, got_qualified)

    def test_regional_without_tops_awards_no_direct_invites(self):
        num_players = 24
        Event2025Factory(
            players=num_players,
            category=Event.Category.REGIONAL,
            date=INVITATIONAL_SPRING_2025.start_date,
        )
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = [QualificationType.LEADERBOARD] * (num_players)
        self.assertEqual(want_qualified, got_qualified)

    def test_regulars_award_no_direct_invites(self):
        num_players = 16
        Event2025Factory(
            players=num_players,
            category=Event.Category.REGULAR,
            date=INVITATIONAL_SPRING_2025.start_date,
        )
        got_qualified = [s.qualification_type for s in self.compute_scores().values()]
        want_qualified = [QualificationType.LEADERBOARD] * num_players
        self.assertEqual(want_qualified, got_qualified)

    def test_leaderboard_awards_no_byes(self):
        num_players = 100
        Event2025Factory(
            players=num_players,
            category=Event.Category.PREMIER,
            date=INVITATIONAL_SPRING_2025.start_date,
            with_tops=8,
        )
        got_scores = self.compute_scores()
        got_byes = [s.byes for s in got_scores.values()]
        self.assertEqual([0] * num_players, got_byes)
