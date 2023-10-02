from dataclasses import dataclass
from typing import Callable
from . import views


@dataclass
class Importer:
    name: str
    view: Callable

    def to_url(self):
        return f"results/create/{self.name.lower()}"

    @property
    def view_name(self):
        return f"results_create_{self.name.lower()}"


IMPORTER_LIST = [
    Importer("Aetherhub", views.CreateAetherhubResultsView.as_view()),
    Importer("EventLink", views.CreateEventlinkResultsView.as_view()),
    Importer("MTGEvent", views.CreateMtgEventResultsView.as_view()),
    Importer("Challonge", views.CreateChallongeResultsView.as_view()),
    # TODO Enable this once parser's ready
    # Importer("Excel", views.CreateExcelResultsView.as_view()),
    Importer("Manual", views.CreateManualResultsView.as_view()),
]
