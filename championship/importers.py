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

import re
from dataclasses import dataclass
from typing import Callable

from . import views


@dataclass
class Importer:
    name: str
    view: Callable

    def clean_name(self):
        return re.sub(r"[^a-zA-Z0-9\s]", "", self.name.lower())

    def to_url(self):
        return f"results/create/{self.clean_name()}"

    @property
    def view_name(self):
        return f"results_create_{self.clean_name()}"


IMPORTER_LIST = [
    # keep-sorted start
    Importer("Aetherhub", views.AetherhubResultsView.as_view()),
    Importer("Challonge", views.ChallongeHtmlResultsView.as_view()),
    Importer("EventLink", views.EventlinkResultsView.as_view()),
    Importer("MTGEvent", views.MtgEventResultsView.as_view()),
    Importer("Melee", views.MeleeResultsView.as_view()),
    # keep-sorted end
    Importer("Excel/CSV", views.ExcelCsvResultsView.as_view()),
    Importer("Manual", views.ManualResultsView.as_view()),
]
