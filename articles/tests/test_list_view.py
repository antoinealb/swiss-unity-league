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

import datetime

from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK

from articles.factories import ArticleFactory


class ArticleArchiveTest(TestCase):
    def test_list_includes_all_published_articles(self):
        published = [
            ArticleFactory(publication_time=d)
            for d in [
                datetime.date(2011, 1, 1),
                datetime.date(2010, 1, 1),
            ]
        ]
        # Add an unpublished article
        ArticleFactory(publication_time=None)
        ArticleFactory(publication_time=datetime.date(2050, 1, 1))
        resp = self.client.get(reverse("article-list"))

        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.assertListEqual(published, list(resp.context["articles"]))

    def test_list_includes_link_to_article(self):
        a = ArticleFactory(publication_time=datetime.date(2011, 1, 1))
        resp = self.client.get(reverse("article-list"))
        want_url = reverse("article-details", args=[2011, 1, 1, a.slug])
        self.assertIn(want_url, resp.content.decode())

    def test_link_is_included_in_home_page_if_articles(self):
        ArticleFactory(publication_time=datetime.date(2011, 1, 1))
        want_url = reverse("article-list")
        resp = self.client.get("/")
        self.assertIn(want_url, resp.content.decode())

    def test_no_article_no_link(self):
        ArticleFactory(publication_time=datetime.date(2050, 1, 1))
        want_url = reverse("article-list")
        resp = self.client.get("/")
        self.assertNotIn(want_url, resp.content.decode())
