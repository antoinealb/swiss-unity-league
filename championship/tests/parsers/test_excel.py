from championship.parsers import excel_parser
from unittest import TestCase
import pandas as pd


class ExcelStandingParser(TestCase):
    def setUp(self):
        self.df = pd.read_excel("championship/tests/parsers/excel_ranking.xlsx")
        self.results = excel_parser.parse_standings_page(self.df)

    def test_can_parse(self):
        want = [
            ("Jeremias Wildi", 10, (3, 0, 1)),
        ]
        self.assertEqual(want, self.results[:3])
