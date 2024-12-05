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

from datetime import date

from django.test import TestCase

from championship.factories import ResultFactory
from championship.models import Result
from championship.season import SEASON_2023


class ResultFactoryTest(TestCase):
    def test_score_is_computed_automatically(self):
        p = ResultFactory(win_count=3, draw_count=1)
        self.assertEqual(10, p.points)


class ResultTest(TestCase):
    def test_str(self):
        p = ResultFactory(win_count=3, draw_count=0, loss_count=2)
        self.assertEqual(
            f"{p.player.name}@{p.event.name} {p.event.get_category_display()} (3-2-0)",
            str(p),
        )

    def test_query_season(self):
        r = ResultFactory(event__date=date(2023, 8, 1))
        ResultFactory(event__date=date(2024, 8, 1))
        self.assertQuerysetEqual(Result.objects.in_season(SEASON_2023), [r])
