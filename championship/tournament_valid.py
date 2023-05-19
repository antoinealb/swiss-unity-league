import math
from championship.models import Event


def get_max_rounds(num_players, event_category):
    if event_category == Event.Category.REGULAR:
        return None

    max_rounds = math.ceil(math.log2(num_players))
    # For regional tournaments without top 8 we allow up to 5 Swiss rounds
    if event_category == Event.Category.REGIONAL and max_rounds < 5:
        max_rounds = 5

    if event_category == Event.Category.PREMIER and num_players < 17:
        raise ValueError(
            "SUL Premier events require at least 17 players. Please downgrade your event to Regional."
        )
    return max_rounds


def simulate_tournament_max_points(num_players, max_rounds):
    points = [0] * num_players
    for i in range(max_rounds):
        for i in range(num_players):
            if i % 2 == 0:
                points[i] += 3
        points.sort(reverse=True)
    return points


def check_if_valid_tournament(standings, event_category):
    if event_category == Event.Category.REGULAR:
        return

    swiss_round_text = (
        " Did you use the standings of the last Swiss round of your tournament?"
    )
    num_players = len(standings)

    max_rounds = get_max_rounds(num_players, event_category)
    at_maximum_text = ""
    if event_category == Event.Category.REGIONAL:
        at_maximum_text = " at maximum"

    event_category_label = event_category
    max_rounds_text = f" A {event_category_label} event with {num_players} players should have{at_maximum_text} {max_rounds} rounds."
    max_points_per_player = 3 * max_rounds

    for name, points in standings:
        if points > max_points_per_player:
            raise ValueError(
                f"Player {name} has too many match points."
                + max_rounds_text
                + f" Hence a player can earn at most {max_points_per_player} match points."
                + swiss_round_text
            )

    total_points = sum(points + (points % 3) * 0.5 for _, points in standings)
    # If the number is not divisible by 3 we know the excess is draws and we add 0.5 so that draws are also 3 points in total
    round_even_num_players = num_players + (
        num_players % 2
    )  # We round up to even number due to byes
    max_possible_points = round_even_num_players * max_rounds * 1.5
    if total_points > max_possible_points:
        raise ValueError(
            "Your tournament hands out too many match points among all players."
            + max_rounds_text
            + swiss_round_text
        )

    if num_players >= 8:
        # If the top competitors in total have more points, than the maximum possible in a simulation something is wrong.
        max_points_top_8 = sum(
            simulate_tournament_max_points(num_players, max_rounds)[:8]
        )
        total_points_top_8 = sum([points for name, points in standings[:8]])
        if total_points_top_8 > max_points_top_8:
            raise ValueError(
                "Your top 8 players have too many points." + swiss_round_text
            )
