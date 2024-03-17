import doctest

import championship.views.results
from championship import admin, views
from championship.parsers import general_parser_functions


def load_tests(loader, tests, ignore):
    # Add all modules where you want doctests to be found here
    tests.addTests(doctest.DocTestSuite(views))
    tests.addTests(doctest.DocTestSuite(championship.views.results))
    tests.addTests(doctest.DocTestSuite(admin))
    tests.addTests(doctest.DocTestSuite(general_parser_functions))
    return tests
