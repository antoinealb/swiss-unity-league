from championship.parsers import aetherhub
from unittest import TestCase
from .utils import load_test_html


class AetherhubStandingsParser(TestCase):
    def setUp(self):
        self.text = load_test_html("aetherhub_ranking.html")
        self.results = aetherhub.parse_standings_page(self.text)

    def test_parse_standings(self):
        want_standings = [
            ("DarioMazzola", 13),
            ("Dominik Horber", 13),
            ("Christopher Weber", 12),
        ]
        self.assertEqual(want_standings, self.results[:3])
