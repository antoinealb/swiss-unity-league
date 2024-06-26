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
from django.urls import reverse

from parameterized import parameterized

from championship.season import SEASONS_WITH_INFO


class InfoPlayerViewTest(TestCase):
    @parameterized.expand(SEASONS_WITH_INFO)
    def test_seasons_exist(self, season):
        url = reverse("info_for_season", kwargs={"slug": season.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, f"championship/info/{season.slug}/info_player.html"
        )

    def test_default_info_exists(self):
        response = self.client.get(reverse("info"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("info_for_season", kwargs={"slug": "foobar"})
        )
        self.assertEqual(response.status_code, 404)


class InfoOrganizerViewTest(TestCase):
    @parameterized.expand(SEASONS_WITH_INFO)
    def test_seasons_exist(self, season):
        url = reverse("info_organizer_for_season", kwargs={"slug": season.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, f"championship/info/{season.slug}/info_organizer.html"
        )

    def test_default_info_exists(self):
        response = self.client.get(reverse("info_organizer"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("info_organizer_for_season", kwargs={"slug": "foobar"})
        )
        self.assertEqual(response.status_code, 404)
