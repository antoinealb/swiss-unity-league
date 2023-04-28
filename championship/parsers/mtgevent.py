from bs4 import BeautifulSoup
from .general_parser_functions import record_to_points, find_index_of_substring


def _standings(soup):
    table = soup.find(
        "table", {"class": "MuiTable-root", "aria-label": "Results table"}
    )
    titles = [tag.text.strip() for tag in table.find("thead").find_all("th")]
    player_index = find_index_of_substring(titles, "Player")
    record_index = find_index_of_substring(titles, "Record")
    for line in table.find("tbody").find_all("tr"):
        values = [tag.text.strip() for tag in line.find_all(["th", "td"])]
        name = values[player_index]
        points = record_to_points(values[record_index])
        yield (name, points)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
