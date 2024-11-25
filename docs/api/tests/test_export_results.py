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

import csv
import datetime
import io
import os.path
import shlex
import subprocess

from django.test import LiveServerTestCase

from championship.factories import ResultFactory


class CreateEventApiExample(LiveServerTestCase):
    def setUp(self):
        self.result = ResultFactory(event__date=datetime.date(2024, 1, 1))

    def read_exported_data(self):
        file = os.path.dirname(os.path.abspath(__file__))
        file = os.path.join(file, "..", "export_results_to_csv.py")
        cmd = f"{file} --url {self.live_server_url}"
        output = subprocess.check_output(shlex.split(cmd), encoding="utf-8-sig")
        return csv.DictReader(io.StringIO(output))

    def test_download_results(self):
        reader = self.read_exported_data()
        line = next(reader)
        self.assertEqual(line["player"], self.result.player.name)
        self.assertEqual(line["date"], "2024-01-01")
        self.assertEqual(line["event"], self.result.event.name)
        self.assertEqual(int(line["wins"]), self.result.win_count)
        self.assertEqual(int(line["losses"]), self.result.loss_count)
        self.assertEqual(int(line["draws"]), self.result.draw_count)
