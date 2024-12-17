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

from django.db import IntegrityError
from django.test import TestCase

from championship.models import Player, PlayerSeasonData


class PlayerSeasonDataTestCase(TestCase):

    def test_player_season_slug_unique(self):
        player = PlayerSeasonData.objects.create(
            player=Player.objects.create(name="Test Player"),
            season_slug="2023",
            country="US",
        )
        with self.assertRaises(IntegrityError):
            PlayerSeasonData.objects.create(
                player=player.player,
                season_slug="2023",
                country="CA",
            )
