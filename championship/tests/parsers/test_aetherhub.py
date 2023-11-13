from championship.parsers import aetherhub
from unittest import TestCase
from .utils import load_test_html


class AetherhubStandingsParser(TestCase):
    def setUp(self):
        self.text = load_test_html("aetherhub_ranking.html")
        self.results = aetherhub.parse_standings_page(self.text)

    def test_parse_standings(self):
        want_standings = [
            ("DarioMazzola", 13, (4, 0, 1), "https://aetherhub.com/Deck/Public/795680"),
            (
                "Dominik Horber",
                13,
                (4, 0, 1),
                None,
            ),
            (
                "Christopher Weber",
                12,
                (4, 1, 0),
                "https://aetherhub.com/Deck/Public/796591",
            ),
        ]
        got_result = [
            (pr.name, pr.points, pr.record, pr.decklist_url) for pr in self.results[:3]
        ]
        self.assertEqual(want_standings, got_result)
