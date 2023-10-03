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


if __name__ == "__main__":
    unittest.main()
