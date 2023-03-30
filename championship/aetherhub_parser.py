import re
from collections import namedtuple
from bs4 import BeautifulSoup

AetherhubResult = namedtuple("AetherhubResult", ["standings", "round_count"])


def _standings(soup):
    matchs = soup.find(id="tab_results").find("tbody")

    def _value(row, name):
        return row[col_idxs[name]].text.rstrip().strip()

    thead = soup.find(id="tab_results").find("thead")

    col_idxs = {
        cell.text.rstrip().strip(): i for i, cell in enumerate(thead.find_all("th"))
    }

    for row in matchs.find_all("tr"):
        row = [s for s in row.find_all("td")]
        name = _value(row, "Name")
        points = int(_value(row, "Points"))
        yield (name, points)


def _round_count(soup):
    pairing_text = soup.find("a", href="#tab_pairings").text
    num_rounds = re.match(" Pairings round ([0-9]+)", pairing_text).group(1)
    return int(num_rounds)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    round_count = _round_count(soup)
    return AetherhubResult(round_count=round_count, standings=standings)
