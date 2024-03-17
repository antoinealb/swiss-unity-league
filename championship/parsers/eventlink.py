from bs4 import BeautifulSoup

from championship.parsers.general_parser_functions import parse_record
from championship.parsers.parse_result import ParseResult


def _standings(soup):
    standings = soup.find(class_="standings")
    if not standings:
        raise ValueError("No standings found")

    def clean(elem):
        return elem.text.rstrip().strip()

    for row in standings.find("tbody").find_all("tr"):
        name = clean(row.find(class_="name").string)
        points = int(clean(row.find(class_="points").string))
        win_loss_draw = parse_record(row.find(class_="wldb").string)
        yield ParseResult(
            name=name,
            points=points,
            record=win_loss_draw,
        )


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
