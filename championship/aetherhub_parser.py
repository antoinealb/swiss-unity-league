from bs4 import BeautifulSoup


def parse_standings_page(text):
    soup = BeautifulSoup(text, features="html.parser")

    thead = soup.find(id="tab_results").find("thead")

    col_idxs = {
        cell.text.rstrip().strip(): i for i, cell in enumerate(thead.find_all("th"))
    }

    matchs = soup.find(id="tab_results").find("tbody")

    def _value(row, name):
        return row[col_idxs[name]].text.rstrip().strip()

    for row in matchs.find_all("tr"):
        row = [s for s in row.find_all("td")]
        name = _value(row, "Name")
        points = int(_value(row, "Points"))
        results = _value(row, "Results")
        yield (name, points, results)
