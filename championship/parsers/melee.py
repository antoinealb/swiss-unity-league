import csv

from championship.parsers.general_parser_functions import parse_record
from championship.parsers.parse_result import ParseResult


def parse_standings(text):
    reader = csv.DictReader(text.splitlines())

    # In Melee export, there can be several phases, and we will have standings
    # for every phase appended. We only take the last phase here.
    result_per_player = {}
    for line in reader:
        first, last = line["FirstName"], line["LastName"]
        wins = int(line["MatchWins"])
        loses = int(line["MatchLoses"])
        draws = int(line["MatchDraws"])
        points = int(line["Points"])
        rank = int(line["Rank"])
        name = f"{first} {last}"
        result_per_player[name] = (rank, name, points, (wins, loses, draws))

    # Now the dict contains deduplicate entries
    return [
        ParseResult(name, points, standings)
        for (rank, name, points, standings) in sorted(result_per_player.values())
    ]
