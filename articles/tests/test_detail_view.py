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
from rest_framework.status import HTTP_200_OK

from articles.factories import ArticleFactory
from championship.factories import UserFactory


class ArticleViewTestCase(TestCase):
    def test_can_get_article(self):
        article = ArticleFactory(publication_time=datetime.date(2020, 1, 1))

        args = [
            article.publication_time.year,
            article.publication_time.month,
            article.publication_time.day,
            article.slug,
        ]

        resp = self.client.get(reverse("article-details", args=args))
        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.assertEqual(article, resp.context["article"])

    def test_can_get_unpublished_article(self):
        """
        Unpublished articles do not have a publication date that we can use
        for their URL, so instead they are publised at a special preview url,
        and keyed by their primary key.
        """
        article = ArticleFactory()
        args = [article.id, article.slug]
        resp = self.client.get(reverse("article-preview", args=args))
        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.assertEqual(article, resp.context["article"])

    def test_no_edit_button_for_allowed_user(self):
        article = ArticleFactory()
        args = [article.id, article.slug]
        resp = self.client.get(reverse("article-preview", args=args))
        edit_url = reverse("article-update", args=args)

        self.assertNotIn(edit_url, resp.content.decode())

    def test_shows_edit_button_for_allowed_user(self):
        user = UserFactory()
        user.user_permissions.add(Permission.objects.get(codename="change_article"))
        self.client.force_login(user)

        article = ArticleFactory()
        args = [article.id, article.slug]
        resp = self.client.get(reverse("article-preview", args=args))
        edit_url = reverse("article-update", args=args)

        self.assertIn(edit_url, resp.content.decode())
