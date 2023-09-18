from championship.parsers import mtgevent
from unittest import TestCase
from .utils import load_test_html


class MtgEventStandingsParser(TestCase):
    def setUp(self):
        self.text = load_test_html("mtgevent_ranking.html")
        self.results = mtgevent.parse_standings_page(self.text)

    def test_can_parse(self):
        want = [
            ("Toni Marty", 9, (3, 1, 0)),
            ("Eder Lars", 9, (3, 1, 0)),
            ("Pascal Merk", 9, (3, 1, 0)),
            ("Luca Riedmann", 9, (3, 1, 0)),
            ("Remus Kosmalla", 6, (2, 2, 0)),
        ]
        self.assertEqual(want, self.results[:5])
