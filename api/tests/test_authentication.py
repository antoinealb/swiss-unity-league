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

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.status import HTTP_200_OK
from rest_framework.test import APITestCase


class ObtainTokenTest(APITestCase):
    def setUp(self):
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)

    def test_obtain_token(self):
        resp = self.client.post(reverse("api_auth_token"), data=self.credentials)
        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.assertIn("token", resp.json())

    def test_wrong_credentials(self):
        self.credentials["password"] = "foo"
        resp = self.client.post(reverse("api_auth_token"), data=self.credentials)
        self.assertNotEqual(HTTP_200_OK, resp.status_code)
