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
from io import BytesIO

from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from PIL import Image

from articles.factories import ArticleFactory
from articles.models import Article
from championship.factories import UserFactory


def get_test_image_file():
    image_io = BytesIO()
    image = Image.new("RGB", (100, 100), color=(255, 0, 0))
    image.save(image_io, format="JPEG")
    image_io.seek(0)
    return SimpleUploadedFile("image.jpg", image_io.read(), content_type="image/jpeg")


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
            "header_image": get_test_image_file(),
            "description": "Hello World",
        }
        resp = self.client.post(self.url, data=data)
        self.article.refresh_from_db()

        self.assertEqual(self.article.title, data["title"])
        self.assertEqual(self.article.content, data["content"])
        self.assertEqual(self.article.description, data["description"])
        self.assertEqual(
            self.article.header_image.url,
            f"{settings.MEDIA_URL}article_header/image.jpg",
        )
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
            "header_image": get_test_image_file(),
            "description": "Hello World",
        }
        resp = self.client.post(self.url, data=data)

        article = Article.objects.first()

        self.assertEqual(article.title, data["title"])
        self.assertEqual(article.content, data["content"])
        self.assertEqual(article.description, data["description"])
        self.assertEqual(
            article.header_image.url,
            f"{settings.MEDIA_URL}article_header/image.jpg",
        )

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


class ArticleDraftTest(TestCase):
    def test_list_article_draft(self):
        article = ArticleFactory()
        # Another article by same author, but not a draft anymore
        ArticleFactory(
            author=article.author, publication_time=datetime.date(2020, 1, 1)
        )
        ArticleFactory()  # another author

        article.author.user_permissions.add(
            Permission.objects.get(codename="add_article")
        )
        self.client.force_login(article.author)
        resp = self.client.get(reverse("article-drafts"))
        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.assertEqual([article], list(resp.context["articles"]))

    def test_permission_denied(self):
        u = UserFactory()
        self.client.force_login(u)

        resp = self.client.get(reverse("article-drafts"))
        self.assertEqual(HTTP_403_FORBIDDEN, resp.status_code)

    def test_in_menu(self):
        u = UserFactory()
        u.user_permissions.add(Permission.objects.get(codename="add_article"))
        want_url = reverse("article-drafts")
        self.assertNotIn(want_url, self.client.get("/").content.decode())

        self.client.force_login(u)
        self.assertIn(want_url, self.client.get("/").content.decode())


class FileUploadViewTestCasse(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user.user_permissions.add(Permission.objects.get(codename="add_article"))
        self.client.force_login(self.user)

    def test_upload_file(self):
        file = SimpleUploadedFile(
            "hello.txt",
            b"Hello, world!",
            content_type="application/txt",
        )
        resp = self.client.post(
            reverse("article-attachment-create"),
            data={"file": file},
            follow=True,
        )
        self.assertEqual(200, resp.status_code)
        self.assertIn("hello.txt", resp.content.decode())

        resp = self.client.get(f"{settings.MEDIA_URL}/articles/hello.txt")
        self.assertEqual(200, resp.status_code)
