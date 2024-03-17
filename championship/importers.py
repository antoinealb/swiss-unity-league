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
    Importer("Aetherhub", views.AetherhubResultsView.as_view()),
    Importer("EventLink", views.EventlinkResultsView.as_view()),
    Importer("MTGEvent", views.MtgEventResultsView.as_view()),
    Importer("Melee", views.MeleeResultsView.as_view()),
    Importer("Challonge", views.ChallongeHtmlResultsView.as_view()),
    Importer("Excel/CSV", views.ExcelCsvResultsView.as_view()),
    Importer("Manual", views.ManualResultsView.as_view()),
]
