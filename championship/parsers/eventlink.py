import re
from bs4 import BeautifulSoup


RECORD_RE = re.compile(r"\s(\d+)/(\d+)/(\d+)\s")


def _standings(soup):
    standings = soup.find(class_="standings")
    thead = standings.find("thead")

    def clean(elem):
        return elem.text.rstrip().strip()

    for row in standings.find("tbody").find_all("tr"):
        name = clean(row.find(class_="name").string)
        points = int(clean(row.find(class_="points").string))
        win_loss_draw = RECORD_RE.match(row.find(class_="wldb").string)
        win_loss_draw = tuple(int(s) for s in win_loss_draw.groups())
        yield (name, points, win_loss_draw)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
