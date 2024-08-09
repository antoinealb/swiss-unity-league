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
from django.test import Client, TestCase
from django.urls import reverse

from championship.factories import PlayerFactory, RankedEventFactory, ResultFactory
from championship.season import SEASON_2023


class TopPlayersEmailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("admin:top_players_emails")
        User.objects.create_user(
            username="test", password="test", is_staff=True, is_superuser=True
        )
        self.client.login(username="test", password="test")
        self.event = RankedEventFactory()
        for i in range(3):
            player = PlayerFactory(email=f"player{i}@example.com")
            ResultFactory(event=self.event, points=i * 3, player=player)

    def test_need_to_be_authorized(self):
        self.client.logout()
        response = self.client.get(self.url)
        # Check that unauthenticated users are redirected
        self.assertEqual(response.status_code, 302)

    def test_post_method(self):
        response = self.client.post(
            self.url, {"num_of_players": 2, "season": SEASON_2023.slug}
        )

        # Check that the status code is 200 (success)
        self.assertEqual(response.status_code, 200)

        # Check that the correct number of players are returned
        self.assertEqual(len(response.context["entries"]), 2)

        emails = response.context["emails"]
        # Check that the emails are correctly formatted
        self.assertEqual(emails, "player2@example.com; player1@example.com")

    def test_hidden_from_leaderboard(self):
        player = PlayerFactory()
        ResultFactory(event=self.event, points=100, player=player)
        response = self.client.post(
            self.url, {"num_of_players": 4, "season": SEASON_2023.slug}
        )

        # Check that first all players are returned
        self.assertEqual(len(response.context["entries"]), 4)
        player.hidden_from_leaderboard = True
        player.save()

        response = self.client.post(
            self.url, {"num_of_players": 4, "season": SEASON_2023.slug}
        )
        # Check that hidden players are not returned
        self.assertEqual(len(response.context["entries"]), 3)
