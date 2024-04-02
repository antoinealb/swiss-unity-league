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

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse

from championship.factories import *
from championship.models import *


class PlayerMergeActionTest(TestCase):
    def setUp(self):
        u = User.objects.create_user(username="test", password="test", is_staff=True)
        self.client = Client()
        self.client.login(username="test", password="test")
        u.user_permissions.add(Permission.objects.get(codename="delete_player"))
        u.user_permissions.add(Permission.objects.get(codename="change_player"))
        u.save()

    def test_merge_players_displays_confirmation(self):
        players = [PlayerFactory() for _ in range(10)]
        data = {"action": "merge_players", "_selected_action": [p.pk for p in players]}

        response = self.client.post(
            reverse("admin:championship_player_changelist"), data, follow=True
        )
        self.assertIn("confirmation", response.content.decode())

    def test_merge_players_confirmed(self):
        players = [PlayerFactory() for _ in range(10)]
        data = {
            "action": "merge_players",
            "_selected_action": [p.pk for p in players],
            "player_to_keep": players[0].pk,
        }

        self.client.post(
            reverse("admin:championship_player_changelist"), data, follow=True
        )
        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(Player.objects.all()[0].name, players[0].name)

    def test_merge_players_creates_aliases(self):
        players = [PlayerFactory() for _ in range(10)]
        data = {
            "action": "merge_players",
            "_selected_action": [p.pk for p in players],
            "player_to_keep": players[0].pk,
        }

        self.client.post(
            reverse("admin:championship_player_changelist"), data, follow=True
        )

        self.assertEqual(PlayerAlias.objects.count(), 9)
        self.assertEqual(
            [p.name for p in PlayerAlias.objects.all()], [p.name for p in players[1:]]
        )

    def test_merge_player_emails(self):
        EXAMPLE_EMAIL = "example@email.com"
        mergeToPlayer = PlayerFactory()
        mergeFromPlayer = PlayerFactory(email=EXAMPLE_EMAIL)
        data = {
            "action": "merge_players",
            "_selected_action": [
                mergeToPlayer.pk,
                PlayerFactory().pk,
                mergeFromPlayer.pk,
                PlayerFactory().pk,
            ],
            "player_to_keep": mergeToPlayer.pk,
        }

        self.client.post(
            reverse("admin:championship_player_changelist"), data, follow=True
        )
        mergeToPlayer.refresh_from_db()
        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(mergeToPlayer.email, EXAMPLE_EMAIL)
