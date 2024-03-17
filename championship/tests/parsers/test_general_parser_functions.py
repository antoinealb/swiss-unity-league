import unittest

from parameterized import parameterized

from championship.parsers.general_parser_functions import *


class TestParseRecord(unittest.TestCase):
    @parameterized.expand(
        [("3-0-1", (3, 0, 1)), ("2-0-0", (2, 0, 0)), ("1/1/1", (1, 1, 1))]
    )
    def test_parse_valid_record_with_draw(self, record, expected_record):
        record = parse_record(record)
        self.assertEqual(record, expected_record)

    @parameterized.expand([("3-0", (3, 0, 0)), ("2-0", (2, 0, 0)), ("1/1", (1, 1, 0))])
    def test_parse_valid_record_without_draw(self, record, expected_record):
        record = parse_record(record)
        self.assertEqual(record, expected_record)

    @parameterized.expand(["3-a-1", "3-1-x", "a", "3/1-2"])
    def test_parse_invalid_record_raises_exception(self, record):
        with self.assertRaises(ValueError):
            parse_record(record)


class RecordToPointsTestCase(unittest.TestCase):
    def test_record_to_points(self):
        self.assertEqual(record_to_points("3-1-0"), 9)
        self.assertEqual(record_to_points("2-2-2"), 8)
        self.assertEqual(record_to_points("0-0-1"), 1)


class TestEstimateRounds(unittest.TestCase):
    def test_single_player(self):
        self.assertEqual(estimate_rounds([3]), 1)

    def test_even_players(self):
        self.assertEqual(estimate_rounds([3, 0]), 1)

    def test_odd_players(self):
        self.assertEqual(estimate_rounds([3, 3, 0]), 1)

    def test_mixed_points(self):
        self.assertEqual(estimate_rounds([3, 4, 5]), 3)

    def test_5_round_5_players(self):
        self.assertEqual(estimate_rounds([11, 10, 9, 7, 6]), 5)

    def test_4_round_5_players(self):
        self.assertEqual(estimate_rounds([10, 9, 7, 6, 3]), 4)

    def test_4_round_9_players(self):
        self.assertEqual(estimate_rounds([12, 9, 6, 6, 6, 5, 5, 4, 4]), 4)

    def test_4_round_13_players(self):
        self.assertEqual(estimate_rounds([12, 10, 9, 7, 7, 6, 6, 6, 4, 4, 4, 3, 3]), 4)

    def test_6_rounds_35_players(self):
        players_matchpoints = (
            [15]
            + [13] * 4
            + [12] * 6
            + [10] * 3
            + [9] * 6
            + [8] * 4
            + [7]
            + [6] * 5
            + [4]
            + [3] * 3
            + [0]
        )
        self.assertEqual(len(players_matchpoints), 35)
        self.assertEqual(
            estimate_rounds(players_matchpoints),
            6,
        )


class ParserFunctionsTest(unittest.TestCase):
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
        row1 = ["player1", "3", "male", "5.4"]
        row2 = ["2", "2", "2.22", "23 ", "65", "female"]
        row3 = ["2", "{}", "player3", "3.5", "male", "active"]
        self.assertEqual(find_non_numeric_index(row1), 0)
        self.assertEqual(find_non_numeric_index(row2), 5)
        self.assertEqual(find_non_numeric_index(row3), 1)

    def test_find_index_of_nth_integer(self):
        row1 = ["{}", "1", "3", "male", "5.4"]
        row2 = ["2 ", "2", "2.22", "23 ", "65", "female"]
        row3 = ["2", "player3", "3.5", "male", "active"]
        self.assertEqual(find_index_of_nth_integer(row1, 1), 1)
        self.assertEqual(find_index_of_nth_integer(row2, 4), 4)
        self.assertEqual(find_index_of_nth_integer(row3, 2), None)


if __name__ == "__main__":
    unittest.main()
