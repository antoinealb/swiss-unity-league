from bs4 import BeautifulSoup
from championship.parsers.general_parser_functions import parse_record


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
        record = parse_record(_value(row, "Results"))

        yield (name, points, record)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
