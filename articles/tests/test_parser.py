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

from parsita import Success

from articles.parser import ArticleTagParser, CardTag, extract_tags


class ParserTest(TestCase):
    def test_parse_text(self):
        res = ArticleTagParser.text.parse("Hello, world")
        self.assertIsInstance(res, Success)

    def test_parse_card_name(self):
        res = ArticleTagParser.card.parse("Fatal Push")
        self.assertIsInstance(res, Success)

    def test_parse_card_name_wrapped(self):
        res = ArticleTagParser.card_tag.parse("[[Fatal Push]]")
        self.assertIsInstance(res, Success)

    def test_parse_multiobject(self):
        res = ArticleTagParser.article.parse("Hello [[Fatal Push]]")
        self.assertIsInstance(res, Success)
        want = ["Hello ", CardTag("Fatal Push")]
        self.assertEqual(want, res.unwrap())

    def test_parse_wrapped_text(self):
        article = """As shown, [[Fatal Push]] is OP."""
        want = ["As shown, ", CardTag("Fatal Push"), " is OP."]
        got = list(extract_tags(article))
        self.assertEqual(want, got)
