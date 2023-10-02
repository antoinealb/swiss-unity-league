from championship.parsers import excel_parser
from unittest import TestCase
import pandas as pd


class ExcelStandingParser(TestCase):
    def setUp(self):
        self.df = pd.read_excel("championship/tests/parsers/excel_ranking.xlsx")
        self.results = excel_parser.parse_standings_page(self.df)

    def test_can_parse(self):
        want = [
            ("Jari Rentsch", 18, (6, 1, 0)),
            ("Noé Dumez", 17, (5, 0, 2)),
            ("RENAUD-GOUD, Antoine", 16, (5, 1, 1)),
        ]
        self.assertEqual(want, self.results[:3])


class ExcelStandingParserExceptions(TestCase):
    def setUp(self):
        self.df = pd.read_excel("championship/tests/parsers/excel_ranking.xlsx")

    def test_player_name_not_found(self):
        del self.df["PLAYER_NAME"]
        with self.assertRaises(excel_parser.PlayerNameNotFound):
            excel_parser.parse_standings_page(self.df)

    def test_record_or_match_points_not_found(self):
        del self.df["RECORD"]
        del self.df["MATCH_POINTS"]
        with self.assertRaises(excel_parser.RecordOrMatchPointsNotFound):
            excel_parser.parse_standings_page(self.df)

    def test_invalid_record(self):
        self.df.loc[0, "RECORD"] = "invalid"
        with self.assertRaises(excel_parser.InvalidRecordError):
            excel_parser.parse_standings_page(self.df)
