from collections import namedtuple
from bs4 import BeautifulSoup

MtgEventResult = namedtuple("AetherhubResult", ["standings"])


def _recordToPoints(record):
    points = 0
    for index, num in enumerate(record.split("-")):
        if index == 0:
            points += int(num) * 3
        if index == 2:
            points += int(num)
    return points


def _standings(soup):
    table = soup.find(
        "table", {"class": "MuiTable-root", "aria-label": "Results table"}
    )
    titles = [tag.text.strip() for tag in table.find("thead").find_all("th")]
    player_index = titles.index("Player")
    record_index = titles.index("Record")
    for line in table.find("tbody").find_all("tr"):
        values = [tag.text.strip() for tag in line.find_all(["th", "td"])]
        name = values[player_index]
        points = _recordToPoints(values[record_index])
        yield (name, points)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
