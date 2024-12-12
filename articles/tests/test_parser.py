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

from parameterized import parameterized
from parsita import Success

from articles.parser import (
    ArticleTagParser,
    CardTag,
    DecklistTag,
    ImageTag,
    extract_tags,
)
from multisite.constants import ALL_DOMAINS


class ParserTest(TestCase):
    def test_parse_text(self):
        res = ArticleTagParser.text.parse("Hello, world")
        self.assertIsInstance(res, Success)

    def test_parse_card_name(self):
        res = ArticleTagParser.card.parse("Fatal Push")
        self.assertIsInstance(res, Success)

    def test_parse_card_name_wrapped(self):
        res = ArticleTagParser.tag.parse("[[Fatal Push]]")
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

    @parameterized.expand(ALL_DOMAINS)
    def test_parse_wrapped_bracket_tag_decklist(self, domain):
        article = f"""Good decklist![[https://{domain}/decklists/ff521f2e-085c-4cc0-901b-600ec9a71dab/]]"""
        want = ["Good decklist!", DecklistTag("ff521f2e-085c-4cc0-901b-600ec9a71dab")]
        got = list(extract_tags(article))
        self.assertEqual(want, got)

    @parameterized.expand(ALL_DOMAINS)
    def test_parse_bracket_tag_decklist(self, domain):
        article = (
            f"""[[http://{domain}/decklists/ff521f2e-085c-4cc0-901b-600ec9a71dab/]]"""
        )
        want = [DecklistTag("ff521f2e-085c-4cc0-901b-600ec9a71dab")]
        got = list(extract_tags(article))
        self.assertEqual(want, got)

    @parameterized.expand(ALL_DOMAINS)
    def test_parse_relative_anchor_decklist(self, domain):
        article = f"""<p>My Article</p><p><a href="../../decklists/a4ec9345-da22-4ad8-a0b6-7cb432da9c24/">https://{domain}/decklists/a4ec9345-da22-4ad8-a0b6-7cb432da9c24/</a></p>"""
        want = [
            "<p>My Article</p><p>",
            DecklistTag("a4ec9345-da22-4ad8-a0b6-7cb432da9c24"),
            "</p>",
        ]
        got = list(extract_tags(article))
        self.assertEqual(want, got)

    @parameterized.expand(ALL_DOMAINS)
    def test_parse_relative_anchor_with_protocol_decklist(self, domain):
        article = f"""<p>My Article</p><p><a href="https://../../decklists/a4ec9345-da22-4ad8-a0b6-7cb432da9c24/">https://{domain}/decklists/a4ec9345-da22-4ad8-a0b6-7cb432da9c24/</a></p>"""
        want = [
            "<p>My Article</p><p>",
            DecklistTag("a4ec9345-da22-4ad8-a0b6-7cb432da9c24"),
            "</p>",
        ]
        got = list(extract_tags(article))
        self.assertEqual(want, got)

    @parameterized.expand(ALL_DOMAINS)
    def test_parse_absolute_anchor_decklist(self, domain):
        article = f"""<p>My Article</p><p><a href="https://{domain}/decklists/a4ec9345-da22-4ad8-a0b6-7cb432da9c24/">https://{domain}/decklists/a4ec9345-da22-4ad8-a0b6-7cb432da9c24/</a></p>"""
        want = [
            "<p>My Article</p><p>",
            DecklistTag("a4ec9345-da22-4ad8-a0b6-7cb432da9c24"),
            "</p>",
        ]
        got = list(extract_tags(article))
        self.assertEqual(want, got)

    @parameterized.expand(ALL_DOMAINS)
    def test_parse_direct_decklist_url(self, domain):
        article = f"""<p>My Article</p><p>https://{domain}/decklists/a4ec9345-da22-4ad8-a0b6-7cb432da9c24</p>"""
        want = [
            "<p>My Article</p><p>",
            DecklistTag("a4ec9345-da22-4ad8-a0b6-7cb432da9c24"),
            "</p>",
        ]
        got = list(extract_tags(article))
        self.assertEqual(want, got)

    def test_parse_image(self):
        txt = "![An image](image/url)"
        want = [ImageTag("image/url", alt_text="An image")]
        got = list(extract_tags(txt))
        self.assertEqual(want, got)
