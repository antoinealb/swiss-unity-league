from championship.parsers import challonge
from championship.parsers.general_parser_functions import *
from unittest import TestCase
from .utils import load_test_html


class ParserFunctionsTest(TestCase):
    def test_find_index_of_substring(self):
        row = ["name", "age", "gender", "height"]
        self.assertEqual(find_index_containing_substring(row, ["age ", "Test"]), 1)
        self.assertEqual(find_index_containing_substring(row, ["gender", "Height"]), 2)
        self.assertEqual(find_index_containing_substring(row, ["weight"]), None)

    def test_find_record_index(self):
        row1 = ["2-2-0", "player2", "6"]
        row2 = ["2-0", "4-[[-0", "4-3-0"]
        row3 = ["player5", "9", "   1   - 1 -4 "]
        self.assertEqual(find_record_index(row1), 0)
        self.assertEqual(find_record_index(row2), 2)
        self.assertEqual(find_record_index(row3), 2)

    def test_find_non_numeric_index(self):
        row1 = ["player1", 3, "male", 5.4]
        row2 = [2, 2, 2.22, "23 ", 65, "female"]
        row3 = [2, {}, "player3", 3.5, "male", "active"]
        self.assertEqual(find_non_numeric_index(row1), 0)
        self.assertEqual(find_non_numeric_index(row2), 5)
        self.assertEqual(find_non_numeric_index(row3), 1)

    def test_find_index_of_nth_integer(self):
        row1 = [{}, 1, 3, "male", 5.4]
        row2 = ["2 ", 2, 2.22, "23 ", 65, "female"]
        row3 = [2, "player3", 3.5, "male", "active"]
        self.assertEqual(find_index_of_nth_integer(row1, 1), 1)
        self.assertEqual(find_index_of_nth_integer(row2, 4), 4)
        self.assertEqual(find_index_of_nth_integer(row3, 2), None)


class ChallongeStandingsParser(TestCase):
    def setUp(self):
        self.text = load_test_html("challonge_new_ranking.html")
        self.results = challonge.parse_standings_page(self.text)
        self.got_standings = [(pr.name, pr.points, pr.record) for pr in self.results]

    def test_can_parse(self):
        want_standings = [
            ("Pascal Richter", 12, (4, 0, 0)),
            ("Guillaume Berclaz", 9, (3, 1, 0)),
            ("Michael Geisser", 9, (3, 1, 0)),
        ]

        self.assertEqual(want_standings, self.got_standings[:3])

    def test_can_parse_draws(self):
        self.assertEqual(("Oliver Schurter", 4, (1, 2, 1)), self.got_standings[9])

    def test_byes_awarded_as_wins(self):
        self.assertEqual(("Jérèmie Boens", 3, (1, 3, 0)), self.got_standings[12])

    def test_byes_not_awarded_for_drops(self):
        """Challonge gives dropped players byes that count as wins. We check, that those are not counted."""
        self.assertEqual(("Daniel Brünisholz", 0, (0, 3, 0)), self.got_standings[13])


class ChallongeSwissRoundsTest(TestCase):
    def test_detects_no_swiss_rounds(self):
        with self.assertRaises(challonge.TournamentNotSwissError):
            self.text = load_test_html("challonge_new_ranking.html").replace(
                "Swiss", "Round Robin"
            )
            self.results = challonge.parse_standings_page(self.text)

    def test_parse_garbage(self):
        with self.assertRaises(AttributeError):
            challonge.parse_standings_page("Foobar")


class ChallongeCleanUrlTest(TestCase):
    def test_positive_clean_url(self):
        tests = [
            (
                "challonge.com/de/rk6vluak",
                "https://challonge.com/rk6vluak/standings",
            ),
            (
                "https://challonge.com/fr/rk6vluak/standings",
                "https://challonge.com/rk6vluak/standings",
            ),
            (
                "https://test.challonge.com/rk6vluak/test",
                "https://challonge.com/rk6vluak/standings",
            ),
            (
                "https://challonge.com/zh_CN/32qwqta",
                "https://challonge.com/32qwqta/standings",
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
            challonge.clean_url("https://challonge.com/zh_CN/32qwqt")
        with self.assertRaises(ValueError):
            challonge.clean_url("https://challonge.com/fr/rk6vlakasa")
