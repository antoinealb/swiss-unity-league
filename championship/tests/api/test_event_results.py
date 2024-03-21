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
        self.event = RankedEventFactory(organizer=self.organizer, date=yesterday)
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
                    "ranking": 1,
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
                    "ranking": 1,
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
        player = PlayerFactory()
        self.client.login(**self.credentials)
        data = {
            "results": [
                {
                    "player": player.name.lower(),
                    "ranking": 1,
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

    def test_upload_deletes_old_results(self):
        player = PlayerFactory()
        self.client.login(**self.credentials)
        data = {
            "results": [
                {
                    "player": player.name,
                    "ranking": 1,
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
