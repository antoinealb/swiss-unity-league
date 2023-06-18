import datetime
from django.test import TestCase, Client
from championship.models import Player, Event
from championship.factories import *
from django.urls import reverse

from championship.views import *


class PlayerDetailsTest(TestCase):
    """
    Tests for the page with a player's details
    """

    def setUp(self):
        self.client = Client()

    def test_score_with_no_results(self):
        """
        Checks that the details page works even when a player has no ranking.

        This happens a lot during manual testing, but could also happen if a
        tournament gets deleted, then we have stale players with 0 points
        """
        player = PlayerFactory()
        response = self.client.get(reverse("player_details", args=[player.id]))
        self.assertIn(player.name, response.content.decode())

    def test_score_in_context(self):
        """
        Checks that we have a score available in the events.
        """
        player = PlayerFactory()
        event = EventFactory(category=Event.Category.PREMIER)
        ep = EventPlayerResult.objects.create(
            points=10, player=player, event=event, ranking=1
        )

        response = self.client.get(reverse("player_details", args=[player.id]))
        gotScore = response.context_data[LAST_RESULTS][0].qps

        self.assertEqual(gotScore, (10 + 3) * 6)

    def test_link_to_event(self):
        """
        Checks that we correctly link to events.
        """
        player = PlayerFactory()
        event = EventFactory(category=Event.Category.PREMIER, id=1234)
        ep = EventPlayerResult.objects.create(
            points=10, player=player, event=event, ranking=1
        )

        response = self.client.get(reverse("player_details", args=[player.id]))
        wantUrl = reverse("event_details", args=[event.id])

        self.assertIn(wantUrl, response.content.decode())

    def test_shows_link_for_admin_page(self):
        client = Client()
        credentials = dict(username="test", password="test")
        user = User.objects.create_user(is_staff=True, **credentials)
        client.login(**credentials)

        player = PlayerFactory()
        resp = client.get(reverse("player_details", args=[player.id]))

        self.assertIn(
            reverse("admin:championship_player_change", args=[player.id]),
            resp.content.decode(),
        )

    def test_attributes(self):
        """
        Checks that the other attributes (ranking and category) are displayed.
        """
        player = PlayerFactory()
        category = Event.Category.PREMIER
        event = EventFactory(category=category)
        ep = EventPlayerResult.objects.create(
            points=10, player=player, event=event, ranking=1
        )

        response = self.client.get(reverse("player_details", args=[player.id]))
        decoded = response.content.decode()
        self.assertIn(category.label, decoded)
        self.assertIn("1st", decoded)

    def test_qp_table(self):
        player = PlayerFactory()
        event = EventFactory(category=Event.Category.PREMIER, id=1234)
        EventPlayerResult.objects.create(
            points=10,
            player=player,
            event=event,
            ranking=1,
            single_elimination_result=EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
        )
        event = EventFactory(category=Event.Category.REGULAR, id=12345)
        EventPlayerResult.objects.create(
            points=600, player=player, event=event, ranking=1
        )
        response = self.client.get(reverse("player_details", args=[player.id]))
        qps_premier = (10 + 3) * 6 + 150
        qps_regular = 600 + 3
        expected_tbody = [
            [
                QPS,
                qps_premier,
                0,
                REGULAR_MAX_STRING.format(qps_regular),
                REGULAR_MAX_SCORE + qps_premier,
            ],
            [EVENTS, 1, 0, 1, 2],
        ]
        actual_tbody = response.context[QP_TABLE][TBODY]
        self.assertEqual(expected_tbody, actual_tbody)

    def test_top_finishes(self):
        player = PlayerFactory()
        event = EventFactory(category=Event.Category.PREMIER, id=1234)
        premier_elim_result = EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST
        EventPlayerResult.objects.create(
            points=10,
            player=player,
            event=event,
            ranking=1,
            single_elimination_result=premier_elim_result,
        )
        event = EventFactory(category=Event.Category.REGIONAL, id=12345)
        EventPlayerResult.objects.create(
            points=10, player=player, event=event, ranking=1
        )
        response = self.client.get(reverse("player_details", args=[player.id]))
        expected_top_finishes = [
            {
                THEAD: [
                    "",
                    Event.Category.PREMIER.label,
                    Event.Category.REGIONAL.label,
                ],
                TBODY: [[SINGLE_ELIM_TO_RANK[premier_elim_result], 1, 0]],
            },
            {
                THEAD: [
                    "",
                    Event.Category.REGIONAL.label,
                    Event.Category.REGULAR.label,
                ],
                TBODY: [["1st", 1, 0]],
            },
        ]
        actual_top_finishes = [
            finish[TABLE] for finish in response.context[TOP_FINISHES]
        ]
        self.assertEqual(expected_top_finishes, actual_top_finishes)
