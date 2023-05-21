from championship.parsers import challonge
from championship.parsers.general_parser_functions import *
from unittest import TestCase
from .utils import load_test_html


class ParserFunctionsTest(TestCase):
    def test_record_to_points(self):
        self.assertEqual(record_to_points("3-1-0"), 9)
        self.assertEqual(record_to_points("2-2-2"), 8)
        self.assertEqual(record_to_points("0-0-1"), 1)

    def test_find_index_of_substring(self):
        row = ["name", "age", "gender", "height"]
        self.assertEqual(find_index_with_substring(row, ["age ", "Test"]), 1)
        self.assertEqual(find_index_with_substring(row, ["gender", "Height"]), 2)
        self.assertEqual(find_index_with_substring(row, ["weight"]), None)

    def test_find_record_index(self):
        row1 = ["2-2-0", "player2", "6"]
        row2 = ["player4", "4-3-0", "4-3-0"]
        row3 = ["player5", "9", "1-1-4"]
        self.assertEqual(find_record_index(row1), 0)
        self.assertEqual(find_record_index(row2), 1)
        self.assertEqual(find_record_index(row3), 2)

    def test_find_non_numeric_index(self):
        row1 = ["player1", 3, "male", 5.4]
        row2 = [2, 2, 2.22, "23", 65, "female"]
        row3 = [2, "player3", 3.5, "male", "active"]
        self.assertEqual(find_non_numeric_index(row1), 0)
        self.assertEqual(find_non_numeric_index(row2), 5)
        self.assertEqual(find_non_numeric_index(row3), 1)


class ChallongeStandingsParser(TestCase):
    def test_can_parse_en(self):
        self.text = load_test_html("challonge_en_ranking.html")
        self.results = challonge.parse_standings_page(self.text)
        want_standings = [
            ("Dario Maz", 10),
            ("Aleks Col", 10),
            ("Antoine Alb", 9),
        ]
        self.assertEqual(want_standings, self.results[:3])

    def test_can_parse_de(self):
        self.text = load_test_html("challonge_de_ranking.html")
        self.results = challonge.parse_standings_page(self.text)
        want_standings = [
            ("Jari Rentsch", 10),
            ("Aleksander Colovic", 9),
            ("Derek Kwan", 9),
            ("Mikko Tuhkannen", 9),
        ]
        self.assertEqual(want_standings, self.results[:4])


class ChallongeCleanUrlTest(TestCase):
    def test_positive_clean_url(self):
        tests = [
            (
                "challonge.com/de/rk6vluak",
                "https://challonge.com/rk6vluak/standings",
            ),
            (
                "https://test.test.challonge.com/zh_cn/rk6vluak",
                "https://test.test.challonge.com/rk6vluak/standings",
            ),
            (
                "https:/test.test.challonge.com/rk6vluak",
                "https://challonge.com/rk6vluak/standings",
            ),
            (
                "https://challonge.com/fr/rk6vluak/standings",
                "https://challonge.com/rk6vluak/standings",
            ),
            (
                "https://test.challonge.com/rk6vluak/test",
                "https://test.challonge.com/rk6vluak/standings",
            ),
        ]

        for input, want in tests:
            with self.subTest(f"Formatting {input}"):
                self.assertEqual(challonge.clean_url(input), want)

    def test_no_challonge(self):
        with self.assertRaises(ValueError):
            challonge.clean_url("llonge.com/rk6vluak")

    def test_wrong_tourney_id(self):
        with self.assertRaises(ValueError):
            challonge.clean_url("https://challonge.com/fr/rk6vlak")
        with self.assertRaises(ValueError):
            challonge.clean_url("https://challonge.com/fr/rk6vlakasdd")
