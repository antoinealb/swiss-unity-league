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

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from articles.factories import ArticleFactory
from articles.models import Article
from championship.factories import UserFactory


class ArticleUpdateTestCase(TestCase):
    def setUp(self):
        self.article = ArticleFactory(publication_time=datetime.date(2020, 1, 1))
        args = [self.article.id, self.article.slug]
        self.url = reverse("article-update", args=args)
        self.user = UserFactory()
        self.user.user_permissions.add(
            Permission.objects.get(codename="change_article")
        )

    def test_redirects_to_login(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse("login") + f"?next={self.url}")

    def test_unauthorized_user(self):
        unauthorized_user = UserFactory()
        self.client.force_login(unauthorized_user)
        resp = self.client.get(self.url)
        self.assertEqual(HTTP_403_FORBIDDEN, resp.status_code)

    def test_authorized_user(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(HTTP_200_OK, resp.status_code)

    def test_post_change(self):
        self.client.force_login(self.user)
        data = {
            "title": "Hello World",
            "content": "<b>Hallo Welt</b>",
            "publication_time": "11/26/2022",
        }
        resp = self.client.post(self.url, data=data)
        self.article.refresh_from_db()

        self.assertEqual(self.article.title, data["title"])
        self.assertEqual(self.article.content, data["content"])
        self.assertEqual(self.article.publication_time, datetime.date(2022, 11, 26))

        self.assertRedirects(resp, self.article.get_absolute_url())


class ArticleCreateTestCase(TestCase):
    def setUp(self):
        self.url = reverse("article-create")
        self.user = UserFactory()
        self.user.user_permissions.add(Permission.objects.get(codename="add_article"))

    def test_redirects_to_login(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse("login") + f"?next={self.url}")

    def test_unauthorized_user(self):
        unauthorized_user = UserFactory()
        self.client.force_login(unauthorized_user)
        resp = self.client.get(self.url)
        self.assertEqual(HTTP_403_FORBIDDEN, resp.status_code)

    def test_authorized_user(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(HTTP_200_OK, resp.status_code)

    def test_post_add(self):
        self.client.force_login(self.user)
        data = {
            "title": "Hello World",
            "content": "<b>Hallo Welt</b>",
            "publication_time": "11/26/2022",
        }
        resp = self.client.post(self.url, data=data)

        article = Article.objects.first()

        self.assertEqual(article.title, data["title"])
        self.assertEqual(article.content, data["content"])
        self.assertEqual(article.publication_time, datetime.date(2022, 11, 26))

        self.assertEqual(article.author, self.user)

        self.assertRedirects(resp, article.get_absolute_url())


class MenuTestCase(TestCase):
    """Checks whether we correctly display menu items to the user."""

    def setUp(self):
        self.url = reverse("article-create")
        self.user = UserFactory()
        self.user.user_permissions.add(Permission.objects.get(codename="add_article"))

    def test_anonymous_user_does_not_get_shown_create_men(self):
        resp = self.client.get("/")
        self.assertNotIn(reverse("article-create"), resp.content.decode())

    def test_authorized_user(self):
        self.client.force_login(self.user)
        resp = self.client.get("/")
        self.assertIn(reverse("article-create"), resp.content.decode())
