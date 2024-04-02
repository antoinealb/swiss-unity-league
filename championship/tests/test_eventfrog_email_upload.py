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

import os

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from championship.factories import PlayerFactory


class EventfrogMailUploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("admin:email_upload_eventfrog")
        User.objects.create_user(
            username="test", password="test", is_staff=True, is_superuser=True
        )

        file = open("championship/tests/eventfrog-ticketexport.xlsx", "rb")

        self.data = {
            "file": file,
        }

    def login(self):
        self.client.login(username="test", password="test")

    def test_need_to_be_authorized(self):
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 302)
        login_url = reverse("admin:login")
        expected_redirect_url = f"{login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url)

    def test_upload(self):
        self.login()
        player = PlayerFactory(name="David Bürge")
        self.client.post(self.url, self.data)
        player.refresh_from_db()
        self.assertEqual(player.email, "dave.buerge@gmail.com")
