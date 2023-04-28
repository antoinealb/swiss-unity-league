class Parser:
    def __init__(self, name):
        self.name = name

    def to_tuple(self):
        return (self.name.upper(), self.name)

    def to_url(self, withSlash=False):
        url = "results/create/" + self.name.lower()
        if withSlash:
            return "/" + url
        else:
            return url

    def to_view_name(self):
        return "results_create_" + self.name.lower()


# Define parser_names and parser_views here in the same order.
# They need to be split up, since we get circular import dependencies otherwise.
_parser_names = ["Aetherhub", "EventLink", "MTGEvent"]
PARSER_LIST = [Parser(name) for name in _parser_names]

from . import views

PARSER_VIEWS = [
    views.CreateAetherhubResultsView,
    views.CreateEvenlinkResultsView,
    views.CreateMtgEventResultsView,
]
