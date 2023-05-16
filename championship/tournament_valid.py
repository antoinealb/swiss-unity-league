import math
from championship.models import Event


def get_max_rounds(num_players, event_category):
    """
    Calculates the maximum number of rounds for a tournament based on the number of players and event category.

    Args:
        num_players (int): The number of players in the tournament.
        event_category (Event.Category): The category of the event.

    Raises:
        TooFewPlayersForPremierError: If the event category is PREMIER and there are fewer than 17 players.

    Returns:
        int: The maximum number of rounds for the tournament.
    """
    if event_category == Event.Category.REGULAR:
        return None

    # Premier requires min 17 players
    if event_category == Event.Category.PREMIER and num_players < 17:
        raise TooFewPlayersForPremierError()

    max_rounds = math.ceil(math.log2(num_players))

    # For Regional tournaments without top 8 we allow up to 5 Swiss rounds
    if event_category == Event.Category.REGIONAL and max_rounds < 5:
        return 5

    return max_rounds


def simulate_tournament_max_points(num_players, num_rounds):
    """
    Simulates a Swiss style tournament and calculates the match points earned by each player. In each round the better performing player will win the match.

    Args:
        num_players (int): The number of players in the tournament.
        num_rounds (int): The number of rounds for the tournament.

    Returns:
        list: A list of match points earned by each player.
    """
    points = [0] * num_players
    for i in range(num_rounds):
        for i in range(num_players):
            if i % 2 == 0:
                points[i] += 3
        points.sort(reverse=True)
    return points


def _validate_points_per_player(standings, category):
    """
    Checks that the points earned by each player are inline with the maximum of rounds for the category.

    Args:
        standings (list): A list of tuples containing player names and their respective points.
        category (Event.Category): The category of the event.

    Raises:
        TooManyPointsForPlayerError: If a player has accumulated more points than allowed for the category.
        ToFewPlayersForPremierError: If the event category is PREMIER and there are fewer than 17 players.
    """
    num_players = len(standings)
    max_rounds = get_max_rounds(num_players, category)
    max_points_per_player = 3 * max_rounds

    for name, points in standings:
        if points > max_points_per_player:
            raise TooManyPointsForPlayerError(name)


def _validate_total_points(standings, category):
    """
    Checks that the total points earned by all players in the standings are less than maximum of points for a given category.

    Args:
        standings (list): A list of tuples containing player names and their respective points.
        category (Event.Category): The category of the event.

    Raises:
        TooManyPointsInTotalError: If the total points earned in the tournament exceed the maximum possible.
        TooFewPlayersForPremierError: If the event category is PREMIER and there are fewer than 17 players.
    """
    num_players = len(standings)
    max_rounds = get_max_rounds(num_players, category)

    # If the points are not divisible by 3 we know the excess is draws and we add 0.5 so that draws also add up to 3 points in total
    estimated_total_points = sum(points + (points % 3) * 0.5 for _, points in standings)

    # We round up to a even number of players due to byes
    rounded_num_players = num_players + num_players % 2

    max_possible_points = rounded_num_players * max_rounds * 1.5

    if estimated_total_points > max_possible_points:
        raise TooManyPointsInTotalError()


def _validate_top_8_points(standings, category):
    num_players = len(standings)
    max_rounds = get_max_rounds(num_players, category)

    if num_players >= 8:
        # If the top competitors in total have more points, than the maximum possible in a simulation something is wrong.
        max_points_top_8 = sum(
            simulate_tournament_max_points(num_players, max_rounds)[:8]
        )
        total_points_top_8 = sum([points for _, points in standings[:8]])
        if total_points_top_8 > max_points_top_8:
            raise TooManyPointsForTop8Error()


def validate_standings(standings, category):
    """
    Validates the standings of a tournament for a given category.

    Args:
        standings (list): A list of tuples containing player names and their respective points.
        category (Event.Category): The category of the event.

    Raises:
        TooManyPointsForPlayerError: If a player has accumulated more points than allowed for the category.
        TooManyPointsInTotalError: If the total points earned in the tournament exceed the maximum possible.
        TooManyPointsForTop8Error: If the top 8 players have accumulated more points than allowed for the category.
        TooFewPlayersForPremierError: If the event category is PREMIER and there are fewer than 17 players.
    """
    if category == Event.Category.REGULAR:
        return

    _validate_points_per_player(standings, category)
    _validate_total_points(standings, category)
    _validate_top_8_points(standings, category)


BASE_VALUE_ERROR_MESSAGE = "The standings are invalid."


def get_max_round_error_message(category, standings):
    """
    Creates an error message based on the category and the standings of an event.

    Args:
        standings (list): A list of tuples containing player names and their respective points.
        category (Event.Category): The category of the event.
    """
    if category != Event.Category.PREMIER:
        at_maximum_text = " at maximum"
    num_players = len(standings)
    max_rounds = get_max_rounds(num_players, category)
    event_category_label = Event.Category(category).label
    return f" A {event_category_label} event with {num_players} players should have{at_maximum_text} {max_rounds} rounds."


class TooManyPointsForPlayerError(ValueError):
    def __init__(self, player, message=BASE_VALUE_ERROR_MESSAGE, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.player = player

    def ui_error_message(self):
        return f"Player {self.player} has too many match points."


class TooManyPointsInTotalError(ValueError):
    def __init__(self, message=BASE_VALUE_ERROR_MESSAGE, *args, **kwargs):
        super().__init__(message, *args, **kwargs)

    def ui_error_message(self):
        return "Your event awards too many points in total."


class TooManyPointsForTop8Error(ValueError):
    def __init__(self, message=BASE_VALUE_ERROR_MESSAGE, *args, **kwargs):
        super().__init__(message, *args, **kwargs)

    def ui_error_message(self):
        return "Your top 8 players have too many points."


class TooFewPlayersForPremierError(ValueError):
    def __init__(self, message=BASE_VALUE_ERROR_MESSAGE, *args, **kwargs):
        super().__init__(message, *args, **kwargs)

    def ui_error_message(self):
        return "SUL Premier events require at least 17 players. Please downgrade your event to Regional."
