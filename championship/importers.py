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
    Importer("EventLink", views.CreateEvenlinkResultsView.as_view()),
    Importer("MTGEvent", views.CreateMtgEventResultsView.as_view()),
]
