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

from django.test import TestCase
from django.utils.html import escape

from articles.templatetags.article import process_article_args
from decklists.factories import DecklistFactory
from multisite.constants import SWISS_DOMAIN
from oracle.factories import CardFactory


class ArticleRenderingTestCase(TestCase):
    databases = ["oracle", "default"]

    def test_no_special_content(self):
        want = "<h1>Hello</h1>"
        got = process_article_args(want)

        self.assertEqual(want, got)

    def setUp(self):
        CardFactory(
            name="Daze",
            scryfall_uri="https://scryfall.com/1234",
            image_uri="https://scryfall.com/img",
        )
        CardFactory(
            name="Fry",
            scryfall_uri="https://scryfall.com/5678",
            image_uri="https://scryfall.com/img",
        )

        self.daze_html = """<a href="#" data-bs-toggle="modal" data-bs-target="#cardModal" data-card-image="https://scryfall.com/img" data-card-url="https://scryfall.com/1234" data-card-name="Daze">Daze</a>"""
        self.fry_html = """<a href="#" data-bs-toggle="modal" data-bs-target="#cardModal" data-card-image="https://scryfall.com/img" data-card-url="https://scryfall.com/5678" data-card-name="Fry">Fry</a>"""

    def test_single_card(self):
        got = process_article_args("[[Daze]]")
        self.assertEqual(self.daze_html, got.rstrip())

    def test_single_card_does_not_exist(self):
        got = process_article_args("[[Farmogoyf]]")
        self.assertEqual("[[Farmogoyf]]", got)

    def test_decklist(self):
        DecklistFactory(
            id="ff521f2e-085c-4cc0-901b-600ec9a71dab",
            content="4 Daze\n\n4 Fry",
        )
        article = f"""
        [[https://{SWISS_DOMAIN}/decklists/ff521f2e-085c-4cc0-901b-600ec9a71dab/]]
        """
        got = process_article_args(article)
        self.assertIn(self.daze_html, got)
        self.assertIn(self.fry_html, got)

    def test_decklist_details(self):
        decklist = DecklistFactory(
            id="ff521f2e-085c-4cc0-901b-600ec9a71dab",
        )
        article = f"""
        [[https://{SWISS_DOMAIN}/decklists/ff521f2e-085c-4cc0-901b-600ec9a71dab/]]
        """
        got = process_article_args(article)
        event = decklist.collection.event
        self.assertIn(escape(decklist.archetype), got)
        self.assertIn(event.name, got)
        self.assertIn(event.get_absolute_url(), got)
        self.assertIn(decklist.player.name, got)
        self.assertIn(decklist.player.get_absolute_url(), got)
        self.assertIn(decklist.collection.get_format_display(), got)

    def test_unknown_decklist(self):
        article = f"""
        [[https://{SWISS_DOMAIN}/decklists/ff521f2e-085c-4cc0-901b-600ec9a71dab/]]
        """
        got = process_article_args(article)
        want = "Unknown decklist"
        self.assertIn(want, got)

    def test_image(self):
        article = "<p>![SMM Metagame](/media/ssm.png)</p>"
        got = process_article_args(article)
        want = (
            '<p><img class="img-fluid" src="/media/ssm.png" alt="SMM Metagame" /></p>'
        )
        self.assertIn(want, got)
