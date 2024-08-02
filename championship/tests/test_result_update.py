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

from django.test import Client, TestCase
from django.urls import reverse

from championship.factories import *
from championship.views import update_ranking_order


class ResultUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="test", password="test")
        self.client.login(username="test", password="test")
        self.to = EventOrganizerFactory(user=self.user)
        self.player = PlayerFactory()
        self.event = EventFactory(organizer=self.to, date=datetime.date.today())
        self.epr = ResultFactory(event=self.event, player=self.player)
        self.url = reverse("epr_edit", args=[self.epr.id])
        self.data = {
            "player_name": self.player.name,
            "win_count": self.epr.win_count,
            "loss_count": self.epr.loss_count,
            "draw_count": self.epr.draw_count,
        }

    def test_update_result_properties(self):
        self.data["win_count"] = 3
        self.data["loss_count"] = 2
        self.data["draw_count"] = 1
        self.client.post(self.url, data=self.data)
        self.epr.refresh_from_db()
        self.assertEqual(self.epr.win_count, 3)
        self.assertEqual(self.epr.loss_count, 2)
        self.assertEqual(self.epr.draw_count, 1)
        self.assertEqual(self.epr.ranking, 1)

    def test_change_deletes_player_without_results(self):
        self.data["player_name"] = "John"
        self.client.post(self.url, data=self.data)
        # Old player is deleted
        players = Player.objects.all()
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].name, "John")

        # Create a second result
        ResultFactory(player=players[0])
        self.data["player_name"] = "Fred"
        self.client.post(self.url, data=self.data)

        # Now old players still exist because he has a result left
        players = Player.objects.all()
        self.assertEqual(len(players), 2)
        self.assertEqual([player.name for player in players], ["John", "Fred"])

    def test_change_player_with_alias(self):
        player_with_alias = PlayerFactory()
        PlayerAlias.objects.create(name="John", true_player=player_with_alias)
        self.data["player_name"] = "John"
        self.client.post(self.url, data=self.data)
        players = Player.objects.all()
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0], player_with_alias)

    def test_change_to_existing_player(self):
        existing_player = PlayerFactory()
        self.data["player_name"] = existing_player.name
        self.client.post(self.url, data=self.data)
        players = Player.objects.all()
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0], existing_player)

    def test_edit_old_event_forbidden(self):
        self.event.date = datetime.date(2023, 1, 1)
        self.event.save()
        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.status_code, 403)

    def test_edit_other_organizer_event_forbidden(self):
        self.event.organizer = EventOrganizerFactory()
        self.event.save()
        response = self.client.post(self.url, data=self.data)
        self.assertEqual(response.status_code, 403)

    def test_update_ranking(self):
        for i in range(9):
            ResultFactory(
                event=self.event, ranking=i, win_count=9 - i, loss_count=0, draw_count=0
            )
        self.data["win_count"] = 10
        self.client.post(self.url, data=self.data)
        results = Result.objects.filter(event=self.event).order_by("ranking")
        self.assertEqual([result.ranking for result in results], list(range(1, 11)))
        self.assertEqual(
            [result.win_count for result in results], list(range(10, 0, -1))
        )
        self.epr.refresh_from_db()
        self.assertEqual(self.epr.ranking, 1)


class UpdateRankingTest(TestCase):
    def setUp(self):
        self.event = EventFactory()
        # Create results with the following win counts
        for win_count in [4, 4, 3, 3, 2, 2, 1, 1, 0, 0]:
            ResultFactory(
                event=self.event,
                win_count=win_count,
                draw_count=0,
            )

        update_ranking_order(self.event)
        self.results = Result.objects.filter(event=self.event).order_by("ranking")
        self.assertEqual(
            [result.ranking for result in self.results], list(range(1, 11))
        )

    def test_update_ranking(self):
        # Result nr 4: change wins 2 => 4
        self.results[4].win_count = 4
        self.results[4].save()

        update_ranking_order(self.event)
        self.results[4].refresh_from_db()
        results = Result.objects.filter(event=self.event).order_by("ranking")
        self.assertEqual(
            [result.win_count for result in results], [4, 4, 4, 3, 3, 2, 1, 1, 0, 0]
        )
        self.assertEqual(self.results[4].ranking, 3)

        # Result nr 7: add draw
        self.results[7].draw_count = 1
        self.results[7].save()
        update_ranking_order(self.event)
        self.results[7].refresh_from_db()
        results = Result.objects.filter(event=self.event).order_by("ranking")
        self.assertEqual(self.results[6].ranking, 7)


class DeleteResultTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="test", password="test")
        self.client.login(username="test", password="test")
        self.to = EventOrganizerFactory(user=self.user)
        self.player = PlayerFactory()
        self.event = EventFactory(organizer=self.to, date=datetime.date.today())
        self.epr = ResultFactory(event=self.event, player=self.player)
        self.url = reverse("single_result_delete", args=[self.epr.id])

    def test_delete_result(self):
        self.assertEqual(Result.objects.count(), 1)
        response = self.client.post(self.url)
        self.assertEqual(Result.objects.count(), 0)
        self.assertEqual(Player.objects.count(), 0)
        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("event_details", args=[self.event.id]))

    def test_delete_several_results_for_player(self):
        ResultFactory(player=self.player)
        self.client.post(self.url)
        self.assertEqual(Result.objects.count(), 1)
        self.assertEqual(Player.objects.count(), 1)

    def test_delete_result_forbidden(self):
        self.event.date = datetime.date(2023, 1, 1)
        self.event.save()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_delete_result_other_organizer_forbidden(self):
        self.event.organizer = EventOrganizerFactory()
        self.event.save()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
