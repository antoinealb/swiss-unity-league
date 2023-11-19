from championship.parsers import melee
from championship.parsers.parse_result import ParseResult
from unittest import TestCase
from .utils import load_test_html


class EventlinkStandingParser(TestCase):
    def setUp(self):
        self.text = load_test_html("melee_standings.csv")
        self.results = melee.parse_standings(self.text)

    def test_can_parse(self):
        want = [
            ParseResult("Antoine Renaud-Goud", 29, (9, 3, 2)),
            ParseResult("Jari Rentsch", 29, (9, 3, 2)),
            ParseResult("Christian Rothen", 28, (9, 4, 1)),
        ]
        l = len(want)
        self.assertEqual(want, self.results[:l])
