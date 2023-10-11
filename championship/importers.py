from dataclasses import dataclass
from typing import Callable
from . import views
import re


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
    Importer("Aetherhub", views.CreateAetherhubResultsView.as_view()),
    Importer("EventLink", views.CreateEventlinkResultsView.as_view()),
    Importer("MTGEvent", views.CreateMtgEventResultsView.as_view()),
    Importer("Challonge", views.CreateChallongeResultsView.as_view()),
    Importer("Excel/CSV", views.CreateExcelCsvResultsView.as_view()),
    Importer("Manual", views.CreateManualResultsView.as_view()),
]
