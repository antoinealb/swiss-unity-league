from championship.parsers import eventlink
from unittest import TestCase
from .utils import load_test_html


class EventlinkStandingParser(TestCase):
    def setUp(self):
        self.text = load_test_html("eventlink_ranking.html")
        self.results = eventlink.parse_standings_page(self.text)

    def test_can_parse(self):
        wantStandings = [
            ("Jeremias Wildi", 10),
            ("Silvan Aeschbach", 9),
            ("Janosh Georg", 7),
        ]
        self.assertEqual(wantStandings, self.results[:3])
