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

import os.path

from django.core.management import call_command
from django.test import TestCase

from oracle.models import Card


class CardTestCase(TestCase):
    def test_str(self):
        c = Card(name="foobar")
        self.assertEqual(str(c), "foobar")


class LoadTestCase(TestCase):
    databases = ["oracle"]

    def test_load_data(self):
        f = os.path.join(os.path.dirname(__file__), "testdata.json")
        call_command("scryfall_import", scryfall_dump=f)
        card = Card.objects.get(oracle_id="0004ebd0-dfd6-4276-b4a6-de0003e94237")
        self.assertEqual(card.name, "Static Orb")
        self.assertEqual(card.mana_cost, "{3}")
