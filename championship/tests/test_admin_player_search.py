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

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from championship.factories import PlayerFactory


class PlayerAdminTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@test.com", "password")
        self.client.force_login(self.user)
        self.url = reverse("admin:championship_player_changelist")
        PlayerFactory(name="Username")
        PlayerFactory(name="Bob Smith")

    def test_search_both_players(self):
        response = self.client.get(self.url, data={"q": "Username Bob"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username")
        self.assertContains(response, "Bob Smith")

    def test_search_one_name(self):
        response = self.client.get(self.url, data={"q": "bob"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Username")
        self.assertContains(response, "Bob Smith")
