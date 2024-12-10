# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.test import TestCase

from parameterized import parameterized

from championship.models import Event
from championship.tournament_valid import (
    TooManyPointsForPlayerError,
    TooManyPointsForTop8Error,
    TooManyPointsInTotalError,
    get_max_round_error_message,
    get_max_rounds,
    simulate_tournament_max_points,
    validate_standings,
)


class CheckTournamentValidTestCase(TestCase):
    def generate_sample_standings(self, points_list):
        """
        Takes a list of points and generates a list of tuples that contain a placeholder player name.
        This is simulates the input that we try to validate.
        """
        return [
            (f"Player {index}", result, (result // 3, result % 3, 0))
            for index, result in enumerate(points_list)
        ]

    @parameterized.expand(
        [
            (12, Event.Category.REGULAR, 6),
            (6, Event.Category.REGIONAL, 5),
            (32, Event.Category.REGIONAL, 5),
            (33, Event.Category.REGIONAL, 6),
            (24, Event.Category.PREMIER, 5),
            (32, Event.Category.PREMIER, 5),
            (33, Event.Category.PREMIER, 6),
        ]
    )
    def test_get_max_rounds(self, num_players, category, expected_result):
        self.assertEqual(expected_result, get_max_rounds(num_players, category))

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
        standings = self.generate_sample_standings([3 * 6, 3 * 3, 0])
        event_category = Event.Category.REGULAR
        # No exception should be raised since maximum is 6 rounds
        validate_standings(standings, event_category)

        standings = self.generate_sample_standings([3 * 6 + 1, 3 * 3, 0])
        with self.assertRaises(TooManyPointsForPlayerError):
            validate_standings(standings, event_category)

    def test_validate_standings_too_many_points_total(self):
        points_list = simulate_tournament_max_points(16, 5)
        standings = self.generate_sample_standings(points_list)
        event_category = Event.Category.REGIONAL
        # No exception should be raised
        validate_standings(standings, event_category)

        # If we add 1 more point an exception should be raised
        standings[15] = ("Player 15", 1, (0, 0, 1))
        with self.assertRaises(TooManyPointsInTotalError):
            validate_standings(standings, event_category)

    def test_validate_standings_single_player_too_many_points(self):
        points_list = simulate_tournament_max_points(32, 5)
        standings = self.generate_sample_standings(points_list)

        event_category = Event.Category.PREMIER
        validate_standings(standings, event_category)  # No exception should be raised

        standings[0] = (
            "Player 1",
            6 * 3,
            (6, 0, 0),
        )  # Give a player too many points for 5 rounds
        with self.assertRaises(TooManyPointsForPlayerError):
            validate_standings(standings, event_category)

    def test_validate_standings_top_8_players(self):
        points_list = [5 * 3] * 8 + [
            0
        ] * 16  # 15 points is possible in 5 rounds, but not for 8 players
        standings = self.generate_sample_standings(points_list)
        event_category = Event.Category.PREMIER
        with self.assertRaises(TooManyPointsForTop8Error):
            validate_standings(standings, event_category)

    def test_get_max_round_error_message(self):
        points_list = [5 * 3] * 8 + [
            0
        ] * 16  # 15 points is possible in 5 rounds, but not for 8 players
        standings = self.generate_sample_standings(points_list)
        event_category = Event.Category.PREMIER

        got = get_max_round_error_message(event_category, standings)
        want = " A Premier event with 24 players should have 5 rounds."
        self.assertEqual(got, want)
