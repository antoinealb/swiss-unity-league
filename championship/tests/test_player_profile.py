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
from django.urls import reverse

from championship.factories import PlayerFactory, PlayerProfileFactory
from championship.models import PlayerAlias, PlayerProfile


class SubmitPlayerProfileViewTest(TestCase):

    def setUp(self):
        self.player = PlayerFactory()
        self.data = {
            "player_name": self.player.name,
            "pronouns": PlayerProfile.Pronouns.SHE_HER,
            "custom_pronouns": "",
            "date_of_birth": "2000-01-01",
            "hometown": "New York",
            "occupation": "Software Engineer",
            "bio": "I love playing Magic!",
            "team_name": "My Team",
            "consent_for_website": True,
            "consent_for_stream": True,
        }

    def test_submit_player_profile(self):
        url = reverse("create_player_profile")
        response = self.client.post(url, self.data)
        self.assertRedirects(response, reverse("index"))
        profile = PlayerProfile.objects.get(player=self.player)
        self.assertEqual(profile.pronouns, PlayerProfile.Pronouns.SHE_HER)
        self.assertEqual(profile.date_of_birth, datetime.date(2000, 1, 1))
        self.assertEqual(profile.hometown, "New York")
        self.assertEqual(profile.occupation, "Software Engineer")
        self.assertEqual(profile.bio, "I love playing Magic!")
        self.assertEqual(profile.team_name, "My Team")
        self.assertTrue(profile.consent_for_website)
        self.assertTrue(profile.consent_for_stream)
        self.assertEqual(profile.status, PlayerProfile.Status.PENDING)

    def test_unknown_player_stays_on_submit_page(self):
        self.data["player_name"] = "Unknown Player"
        url = reverse("create_player_profile")
        response = self.client.post(url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Player 'Unknown Player' does not exist.",
            response.context["form"].errors["__all__"],
        )

    def test_submit_profile_for_player_alias(self):
        PlayerAlias.objects.create(true_player=self.player, name="Alias")
        self.data["player_name"] = "Alias"
        url = reverse("create_player_profile")
        response = self.client.post(url, self.data)
        self.assertRedirects(response, reverse("index"))
        self.assertTrue(PlayerProfile.objects.filter(player=self.player).exists())


class PlayerProfilesByTeamViewTest(TestCase):

    def setUp(self):
        self.url = reverse("player_profiles_by_teams")

    def test_profiles_are_grouped_by_team_name(self):
        PlayerProfileFactory.create_batch(2, team_name="Team A")
        PlayerProfileFactory.create_batch(1, team_name="Team B")
        context = self.client.get(self.url).context

        expected_team_names = ["Team A", "Team B"]
        expected_team_counts = [2, 1]
        self.assertEqual(
            sorted(context["profiles_by_team"].keys()), expected_team_names
        )
        self.assertEqual(
            [len(context["profiles_by_team"][team]) for team in expected_team_names],
            expected_team_counts,
        )

    def test_teamless_profiles_are_shown_separately(self):
        PlayerProfileFactory(team_name="", player__name="Charlie")
        response = self.client.get(self.url)
        context = response.context
        teamless_player_names = [
            profile.player.name for profile in context["teamless_profiles"]
        ]
        self.assertEqual(teamless_player_names, ["Charlie"])

    def test_teams_ordered_by_num_images_first_and_num_bios_second(self):
        PlayerProfileFactory.create_batch(1, team_name="Team A", bio="")
        PlayerProfileFactory.create_batch(2, team_name="Team A", image="")
        # Team B has the same number of images as Team A, but more bios, so it should be ordered second
        PlayerProfileFactory.create_batch(1, team_name="Team B")
        PlayerProfileFactory.create_batch(2, team_name="Team B", image="")
        # Team C has most images and should be ordered first, despite no bios
        PlayerProfileFactory.create_batch(3, team_name="Team C", bio="")

        context = self.client.get(self.url).context
        expected_team_names = ["Team C", "Team B", "Team A"]
        self.assertEqual(
            [team_name for team_name in context["profiles_by_team"].keys()],
            expected_team_names,
        )

    def test_profiles_within_team_ordered_by_image_first_and_bio_second(self):
        PlayerProfileFactory(team_name="Team A", player__name="Alice", image="", bio="")
        # Bob has a bio but no image and should be ordered second
        PlayerProfileFactory(team_name="Team A", player__name="Bob", image="")
        # Charlie has an image and should be ordered first
        PlayerProfileFactory(team_name="Team A", player__name="Charlie", bio="")
        context = self.client.get(self.url).context
        team_a_player_names = [
            profile.player.name for profile in context["profiles_by_team"]["Team A"]
        ]
        self.assertEqual(team_a_player_names, ["Charlie", "Bob", "Alice"])

    def test_redacts_name_of_players(self):
        PlayerProfileFactory(
            player__name="Charlie Brown", player__hidden_from_leaderboard=True
        )
        response = self.client.get(self.url)
        self.assertContains(response, "Charlie B.")
        self.assertNotContains(response, "Charlie Brown")
