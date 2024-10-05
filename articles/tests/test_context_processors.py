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


class ArticleLinkMenuTestCase(TestCase):
    def test_context_processor(self):
        resp = self.client.get("/")
        self.assertFalse(resp.context["has_articles"])

    def test_context_processor_published(self):
        ArticleFactory(publication_time=datetime.date(2010, 1, 1))
        resp = self.client.get("/")
        self.assertTrue(resp.context["has_articles"])
