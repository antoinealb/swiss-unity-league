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

from articles.factories import ArticleFactory


class ArticleTest(TestCase):
    def test_can_create(self):
        a = ArticleFactory()

        self.assertNotEqual("", a.title)
        self.assertNotEqual("", a.content)
        self.assertNotEqual("", a.author.username)

    def test_title_is_slugified(self):
        a = ArticleFactory(title="Hello World")
        self.assertEqual("hello-world", a.slug)
