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

from articles.factories import ArticleFactory
from articles.models import Article


class ArticleTest(TestCase):
    def test_can_create(self):
        a = ArticleFactory()

        self.assertNotEqual("", a.title)
        self.assertNotEqual("", a.content)
        self.assertNotEqual("", a.author.username)

    def test_title_is_slugified(self):
        a = ArticleFactory(title="Hello World")
        self.assertEqual("hello-world", a.slug)

    def test_url(self):
        a = ArticleFactory(
            publication_time=datetime.date(2023, 1, 1), title="Hello World"
        )
        want = "/articles/2023/1/1/hello-world/"
        self.assertEqual(want, a.get_absolute_url())

    def test_url_unpublished(self):
        a = ArticleFactory(title="Hello World")
        want = "/articles/preview/1/hello-world/"
        self.assertEqual(want, a.get_absolute_url())

    def test_url_not_published_yet(self):
        a = ArticleFactory(
            title="Hello World", publication_time=datetime.date(2050, 1, 1)
        )
        want = "/articles/preview/1/hello-world/"
        self.assertEqual(want, a.get_absolute_url())


class ArticleObjectManagerTestCase(TestCase):
    def test_non_yet_published(self):
        ArticleFactory(publication_time=datetime.date(2050, 1, 1))
        self.assertFalse(Article.objects.published().exists())

    def test_non_published(self):
        ArticleFactory(publication_time=None)
        self.assertFalse(Article.objects.published().exists())

    def test_published(self):
        ArticleFactory(publication_time=datetime.date(2010, 1, 1))
        self.assertTrue(Article.objects.published().exists())
