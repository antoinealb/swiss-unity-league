from bs4 import BeautifulSoup
from championship.parsers.general_parser_functions import parse_record
from championship.parsers.parse_result import ParseResult

AH_URL = "https://aetherhub.com"


def _standings(soup):
    matchs = soup.find(id="tab_results").find("tbody")

    def _value(row, name):
        return row[col_idxs[name]].text.rstrip().strip()

    def _get_decklist_url(row):
        deck_field = row[col_idxs.get("Deck", None)]
        if deck_field:
            return deck_field.a.get("href")

    thead = soup.find(id="tab_results").find("thead")

    col_idxs = {
        cell.text.rstrip().strip(): i for i, cell in enumerate(thead.find_all("th"))
    }

    for row in matchs.find_all("tr"):
        row = [s for s in row.find_all("td")]
        name = _value(row, "Name")
        points = int(_value(row, "Points"))
        record = parse_record(_value(row, "Results"))
        decklist_url = AH_URL + _get_decklist_url(row)

        yield ParseResult(
            name=name,
            points=points,
            record=record,
            decklist_url=decklist_url,
        )


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
