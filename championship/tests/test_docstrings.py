import unittest
import doctest
from championship import views
from championship import admin


def load_tests(loader, tests, ignore):
    # Add all modules where you want doctests to be found here
    tests.addTests(doctest.DocTestSuite(views))
    tests.addTests(doctest.DocTestSuite(admin))
    return tests
