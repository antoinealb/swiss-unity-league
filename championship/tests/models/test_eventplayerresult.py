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

from championship.factories import EventPlayerResultFactory


class EventPlayerResultFactoryTest(TestCase):
    def test_score_is_computed_automatically(self):
        p = EventPlayerResultFactory(win_count=3, draw_count=1)
        self.assertEqual(10, p.points)


class EventPlayerResultTest(TestCase):
    def test_str(self):
        p = EventPlayerResultFactory(win_count=3, draw_count=0, loss_count=2)
        self.assertEqual(f"{p.player.name}@{p.event.name} (3-2-0)", str(p))
