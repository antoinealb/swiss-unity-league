from championship.parsers import eventlink
from unittest import TestCase
from .utils import load_test_html


class EventlinkStandingParser(TestCase):
    def setUp(self):
        self.text = load_test_html("eventlink_ranking.html")
        self.results = eventlink.parse_standings_page(self.text)

    def test_can_parse(self):
        want = [
            ("Jeremias Wildi", 10, (3, 0, 1)),
            ("Silvan Aeschbach", 9, (3, 1, 0)),
            ("Janosh Georg", 7, (2, 1, 1)),
        ]
        self.assertEqual(want, self.results[:3])
