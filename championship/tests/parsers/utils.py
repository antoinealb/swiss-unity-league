import os.path


def load_test_html(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path) as f:
        text = f.read()
    return text
