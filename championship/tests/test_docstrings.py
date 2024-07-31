# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import doctest

import championship.views.results
from championship import admin, views
from championship.parsers import general_parser_functions
from championship.templatetags import custom_tags


def load_tests(loader, tests, ignore):
    # Add all modules where you want doctests to be found here
    # keep-sorted start
    tests.addTests(doctest.DocTestSuite(admin))
    tests.addTests(doctest.DocTestSuite(championship.views.results))
    tests.addTests(doctest.DocTestSuite(custom_tags))
    tests.addTests(doctest.DocTestSuite(general_parser_functions))
    tests.addTests(doctest.DocTestSuite(views))
    # keep-sorted end
    return tests
