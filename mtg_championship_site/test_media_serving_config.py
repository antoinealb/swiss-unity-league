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

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client, TestCase


class MediaServingTestCase(TestCase):
    def test_get_media(self):
        filename = "test/test.txt"
        default_storage.save(filename, ContentFile(b"hello"))
        client = Client()
        resp = client.get(f"{settings.MEDIA_URL}/{filename}")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("hello", resp.content.decode())
