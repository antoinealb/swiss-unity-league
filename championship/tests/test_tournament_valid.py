from django.test import TestCase
from championship.tournament_valid import *
from championship.models import Event


class CheckTournamentValidTestCase(TestCase):
    def test_get_max_rounds(self):

        player_category_result_list = [
            (6, Event.Category.REGULAR, None),
            (6, Event.Category.REGIONAL, 5),
            (32, Event.Category.REGIONAL, 5),
            (33, Event.Category.REGIONAL, 6),
            (18, Event.Category.PREMIER, 5),
            (32, Event.Category.PREMIER, 5),
            (33, Event.Category.PREMIER, 6),
        ]
        for num_players, category, result in player_category_result_list:
            self.assertEqual(result, get_max_rounds(num_players, category))

    def test_get_max_rounds_raises_error(self):
        with self.assertRaises(TooFewPlayersForPremierError):
            get_max_rounds(6, Event.Category.PREMIER)

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

    def test_validate_standings_regular(self):
        standings = [("Player 1", 100), ("Player 2", 70), ("Player 3", 50)]
        event_category = Event.Category.REGULAR
        validate_standings(standings, event_category)  # No exception should be raised

    def test_validate_standings_too_many_points_total(self):
        results = simulate_tournament_max_points(16, 5)
        standings = [
            ("Player " + str(index), result) for (index, result) in enumerate(results)
        ]
        event_category = Event.Category.REGIONAL
        # No exception should be raised
        validate_standings(standings, event_category)

        # If we add 1 more point an exception should be raised
        standings[15] = ("Player 15", 1)
        with self.assertRaises(TooManyPointsInTotalError):
            validate_standings(standings, event_category)

    def test_validate_standings_single_player_too_many_points(self):
        results = simulate_tournament_max_points(17, 5)
        standings = [
            ("Player " + str(index), result) for (index, result) in enumerate(results)
        ]
        event_category = Event.Category.PREMIER
        validate_standings(standings, event_category)  # No exception should be raised

        standings[0] = ("Player 1", 6 * 3)  # Give a player too many points for 5 rounds
        with self.assertRaises(TooManyPointsForPlayerError):
            validate_standings(standings, event_category)

    def test_validate_standings_top_8_players(self):
        results = [15] * 8 + [0] * 16
        standings = [
            ("Player " + str(index), result) for (index, result) in enumerate(results)
        ]
        event_category = Event.Category.PREMIER
        with self.assertRaises(TooManyPointsForTop8Error):
            validate_standings(standings, event_category)
