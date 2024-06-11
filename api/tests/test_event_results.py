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

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.status import *
from rest_framework.test import APITestCase

from championship.factories import (
    AddressFactory,
    EventFactory,
    EventOrganizerFactory,
    EventPlayerResultFactory,
    PlayerFactory,
    RankedEventFactory,
)
from championship.models import *
from championship.serializers import EventPlayerResultSerializer, EventSerializer


class TestEventResultsAPI(APITestCase):
    def setUp(self):
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.event = RankedEventFactory(
            organizer=self.organizer, date=yesterday, category=Event.Category.REGIONAL
        )
        self.url = reverse("events-detail", args=[self.event.id])

    def test_event_includes_result(self):
        for i in range(10):
            EventPlayerResultFactory(event=self.event)

        resp = self.client.get(self.url).json()
        self.assertIn("results", resp)

        for result in resp["results"]:
            self.assertIn("win_count", result)
            self.assertIn("loss_count", result)
            self.assertIn("draw_count", result)
            self.assertIn("player", result)
            self.assertIn("single_elimination_result", result)

    def test_send_results(self):
        self.client.login(**self.credentials)
        data = {
            "results": [
                {
                    "player": "Antoine Albertelli",
                    "win_count": 3,
                    "draw_count": 2,
                    "loss_count": 0,
                    "single_elimination_result": 1,
                }
            ],
        }
        resp = self.client.patch(self.url, data=data, format="json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, EventPlayerResult.objects.count())

        e = EventPlayerResult.objects.all()[0]
        self.assertEqual(e.event, self.event)
        self.assertEqual(e.player.name, "Antoine Albertelli")
        self.assertEqual(e.ranking, 1)
        self.assertEqual(e.win_count, 3)
        self.assertEqual(e.loss_count, 0)
        self.assertEqual(e.draw_count, 2)
        self.assertEqual(e.points, 11)
        self.assertEqual(
            e.single_elimination_result,
            EventPlayerResult.SingleEliminationResult.WINNER,
        )

    def test_send_results_player_alias(self):
        player = PlayerFactory()
        PlayerAlias.objects.create(name="Darth Vader", true_player=player)

        self.client.login(**self.credentials)
        data = {
            "results": [
                {
                    "player": "Darth Vader",
                    "win_count": 3,
                    "draw_count": 2,
                    "loss_count": 0,
                    "single_elimination_result": 1,
                }
            ],
        }
        resp = self.client.patch(self.url, data=data, format="json")

        # Check that the event got associated with the player
        self.assertTrue(player.eventplayerresult_set.exists())

    def test_send_results_player_clean_name(self):
        player = PlayerFactory(name="Antoine Albertelli")
        self.client.login(**self.credentials)
        data = {
            "results": [
                {
                    "player": player.name.lower(),
                    "win_count": 3,
                    "draw_count": 2,
                    "loss_count": 0,
                    "single_elimination_result": 1,
                }
            ],
        }
        resp = self.client.patch(self.url, data=data, format="json")

        # Check that the event got associated with the player
        self.assertTrue(
            player.eventplayerresult_set.exists(),
            f"Should have results for {player.name}",
        )

    def test_upload_deletes_old_results(self):
        player = PlayerFactory()
        self.client.login(**self.credentials)
        data = {
            "results": [
                {
                    "player": player.name,
                    "win_count": 3,
                    "draw_count": 2,
                    "loss_count": 0,
                    "single_elimination_result": 1,
                }
            ],
        }

        self.client.patch(self.url, data=data, format="json")
        self.client.patch(self.url, data=data, format="json")

        self.event.refresh_from_db()

        self.assertEqual(1, self.event.eventplayerresult_set.count())

    def test_upload_results_failing_validation(self):
        """Checks that we cannot upload a tournament that do not passes
        validation, same as with manual entry."""
        points_list = [5] * 8 + [0] * 16
        results = [
            dict(
                player=f"Player {i}",
                win_count=points,
                draw_count=0,
                loss_count=0,
                single_elimination_result=None,
            )
            for i, points in enumerate(points_list)
        ]
        self.client.login(**self.credentials)
        resp = self.client.patch(self.url, data={"results": results}, format="json")
        self.assertEqual(400, resp.status_code)
        self.assertEqual(0, self.event.eventplayerresult_set.count())
        self.assertIn("message", resp.json())

    def test_upload_results_failing_validation_but_exemption(self):
        """Checks that we can give exemptions to events in API too."""
        points_list = [5] * 8 + [0] * 16
        results = [
            dict(
                player=f"Player {i}",
                win_count=points,
                draw_count=0,
                loss_count=0,
                single_elimination_result=None,
            )
            for i, points in enumerate(points_list)
        ]

        # Allow the event to submit invalid results
        self.event.results_validation_enabled = False
        self.event.save()

        self.client.login(**self.credentials)
        resp = self.client.patch(self.url, data={"results": results}, format="json")

        self.assertEqual(200, resp.status_code)
        self.assertEqual(24, self.event.eventplayerresult_set.count())

    def test_upload_results_unsorted(self):
        """Checks that results are sorted according to points."""
        points_list = [0] * 2 + [3] * 2
        results = [
            dict(
                player=f"Player {i}",
                win_count=points,
                draw_count=0,
                loss_count=0,
                single_elimination_result=None,
            )
            for i, points in enumerate(points_list)
        ]

        self.client.login(**self.credentials)
        resp = self.client.patch(self.url, data={"results": results}, format="json")

        results = EventPlayerResult.objects.filter(event=self.event).order_by("ranking")
        self.assertEqual(results[0].win_count, 3, "Results should have been sorted.")
        self.assertEqual(
            results[0].player.name, "Player 2", "Results should have been sorted."
        )
