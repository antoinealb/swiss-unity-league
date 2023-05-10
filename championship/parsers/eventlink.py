from bs4 import BeautifulSoup


def _standings(soup):
    standings = soup.find(class_="standings")
    thead = standings.find("thead")

    def clean(elem):
        return elem.text.rstrip().strip()

    for row in standings.find("tbody").find_all("tr"):
        name = clean(row.find(class_="name").string)
        points = int(clean(row.find(class_="points").string))
        yield (name, points)


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")
    standings = list(_standings(soup))
    return standings
