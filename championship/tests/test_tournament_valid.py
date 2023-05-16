from django.test import TestCase
from championship.tournament_valid import *
from championship.models import Event


class CheckTournamentValidTestCase(TestCase):
    def test_get_max_rounds_regular(self):
        num_players = 6
        event_category = Event.Category.REGULAR
        result = get_max_rounds(num_players, event_category)
        self.assertIsNone(result)

    def test_get_max_rounds_regional(self):
        num_players = 6
        event_category = Event.Category.REGIONAL
        result = get_max_rounds(num_players, event_category)
        self.assertEqual(result, 5)

        num_players = 33
        result = get_max_rounds(num_players, event_category)
        self.assertEqual(result, 6)

    def test_get_max_rounds_premier(self):
        num_players = 6
        event_category = Event.Category.PREMIER
        with self.assertRaises(ValueError):
            get_max_rounds(num_players, event_category)

        num_players = 32
        result = get_max_rounds(num_players, event_category)
        self.assertEqual(result, 5)

    def test_simulate_tournament_max_points(self):
        num_players = 8
        max_rounds = 3
        result = simulate_tournament_max_points(num_players, max_rounds)
        expected = [9, 6, 6, 6, 3, 3, 3, 0]
        self.assertEqual(result, expected)

    def test_simulate_tournament_max_points_with_bye(self):
        num_players = 7
        max_rounds = 3
        result = simulate_tournament_max_points(num_players, max_rounds)
        expected = [9, 6, 6, 6, 3, 3, 3]
        self.assertEqual(result, expected)

    def test_check_if_valid_tournament_regular(self):
        standings = [("Player 1", 100), ("Player 2", 70), ("Player 3", 50)]
        event_category = Event.Category.REGULAR
        check_if_valid_tournament(
            standings, event_category
        )  # No exception should be raised

    def test_check_if_valid_tournament_too_many_points_total(self):
        results = simulate_tournament_max_points(16, 5)
        standings = [
            ("Player " + str(index), result) for (index, result) in enumerate(results)
        ]
        event_category = Event.Category.REGIONAL
        check_if_valid_tournament(
            standings, event_category
        )  # No exception should be raised

        standings[15] = (
            "Player 15",
            1,
        )  # If we add 1 more point an exception should be raised
        with self.assertRaises(ValueError) as cm:
            check_if_valid_tournament(standings, event_category)
        self.assertIn(
            "Your tournament hands out too many match points among all players.",
            str(cm.exception),
        )

    def test_check_if_valid_tournament_single_player_too_many_points(self):
        results = simulate_tournament_max_points(17, 5)
        standings = [
            ("Player " + str(index), result) for (index, result) in enumerate(results)
        ]
        event_category = Event.Category.PREMIER
        check_if_valid_tournament(
            standings, event_category
        )  # No exception should be raised

        standings[0] = ("Player 1", 6 * 3)  # too many points for 5 rounds
        standings[1] = (
            "Player 2",
            0,
        )  # Remove some points from player 2 so we don't trigger the other ValueError
        with self.assertRaises(ValueError) as cm:
            check_if_valid_tournament(standings, event_category)
        self.assertIn("Player Player 1 has too many match points.", str(cm.exception))

    def test_check_if_valid_tournament_top_8_players(self):
        results = [15] * 8 + [0] * 16
        standings = [
            ("Player " + str(index), result) for (index, result) in enumerate(results)
        ]
        event_category = Event.Category.PREMIER
        with self.assertRaises(ValueError) as cm:
            check_if_valid_tournament(standings, event_category)
        self.assertIn("Your top 8 players have too many points.", str(cm.exception))
