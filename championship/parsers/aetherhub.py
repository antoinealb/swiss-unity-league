import re
from bs4 import BeautifulSoup

RECORD_REGEXP = re.compile(r"(\d+) - (\d+)(?: - (\d+))?")


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

        m = RECORD_REGEXP.match(_value(row, "Results"))
        record = tuple(int(s or "0") for s in m.groups())

        yield (name, points, record)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
