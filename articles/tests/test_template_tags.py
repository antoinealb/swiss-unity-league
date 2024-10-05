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

from unittest import TestCase

from articles.templatetags.article import process_article_args
from oracle.factories import CardFactory


class ArticleRenderingTestCase(TestCase):
    databases = ["oracle"]

    def test_no_special_content(self):
        want = "<h1>Hello</h1>"
        got = process_article_args(want)

        self.assertEqual(want, got)

    def test_single_card(self):
        CardFactory(
            name="Daze",
            scryfall_uri="https://scryfall.com/1234",
            image_uri="https://scryfall.com/img",
        )
        got = process_article_args("[[Daze]]")
        want = """<a href="#" data-bs-toggle="modal" data-bs-target="#cardModal" data-card-image="https://scryfall.com/img" data-card-url="https://scryfall.com/1234" data-card-name="Daze">Daze</a>"""

        self.assertEqual(want.rstrip(), got.rstrip())
