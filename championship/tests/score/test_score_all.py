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

from django.test import TestCase

from championship.factories import EventFactory, PlayerFactory, ResultFactory
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
            ResultFactory(event=event, player=player, points=3)

        scores = self.compute_scores()
        self.assertEqual(scores[player.id].total_score, 6 * len(SEASONS_WITH_RANKING))
