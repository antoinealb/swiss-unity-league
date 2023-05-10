from championship.parsers import mtgevent
from unittest import TestCase
from .utils import load_test_html


class MtgEventStandingsParser(TestCase):
    def setUp(self):
        self.text = load_test_html("mtgevent_ranking.html")
        self.results = mtgevent.parse_standings_page(self.text)

    def test_can_parse(self):
        wantStandings = [
            ("Toni Marty", 9),
            ("Eder Lars", 9),
            ("Pascal Merk", 9),
            ("Luca Riedmann", 9),
            ("Remus Kosmalla", 6),
            ("Phillpp Ackermann", 6),
            ("Rico Oess", 6),
            ("Mathias Tonazi", 3),
            ("Donat Harterbach", 3),
            ("Pascal Schärrer", 0),
        ]
        self.assertEqual(wantStandings, self.results)
