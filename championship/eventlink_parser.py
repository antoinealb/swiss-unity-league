import re
from collections import namedtuple
from bs4 import BeautifulSoup

EventlinkResult = namedtuple("EventlinkResult", ["standings"])


def _standings(soup):
    standings = soup.find(class_="standings")
    thead = standings.find("thead")

    def clean(elem):
        return elem.text.rstrip().strip()

    for row in standings.find("tbody").find_all("tr"):
        row = list(row.find_all("td"))
        name = clean(row[1])
        points = int(clean(row[2]))
        yield (name, points)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
