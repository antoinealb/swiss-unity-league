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
        event = EventFactory(category=Event.Category.PREMIER)
        ep = EventPlayerResultFactory(
            event=event,
            win_count=3,
            draw_count=1,
            loss_count=0,
        )

        response = self.client.get(reverse("player_details", args=[ep.player.id]))
        gotScore = response.context_data[LAST_RESULTS][0].qps

        self.assertEqual(gotScore, (10 + 3) * 6)

    def test_link_to_event(self):
        """
        Checks that we correctly link to events.
        """
        ep = EventPlayerResultFactory()

        response = self.client.get(reverse("player_details", args=[ep.player.id]))
        wantUrl = reverse("event_details", args=[ep.event.id])

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
        category = Event.Category.PREMIER
        event = EventFactory(category=category)
        ep = EventPlayerResultFactory(event=event, ranking=1)

        response = self.client.get(reverse("player_details", args=[ep.player.id]))
        decoded = response.content.decode()
        self.assertIn(event.category.label, decoded)
        self.assertIn("1st", decoded)

    def test_qp_table(self):
        player = PlayerFactory()
        event = EventFactory(category=Event.Category.PREMIER, id=1234)
        EventPlayerResult.objects.create(
            player=player,
            event=event,
            ranking=1,
            points=10,
            win_count=3,
            loss_count=0,
            draw_count=1,
            single_elimination_result=EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
        )
        event = EventFactory(category=Event.Category.REGULAR, id=12345)
        EventPlayerResult.objects.create(
            player=player,
            event=event,
            ranking=1,
            points=600,
            win_count=200,
            loss_count=0,
            draw_count=0,
        )
        response = self.client.get(reverse("player_details", args=[player.id]))
        qps_premier = (10 + 3) * 6 + 150
        qps_regular = 600 + 3
        expected_tbody = [
            [
                QPS,
                qps_premier,
                0,
                qps_regular,
                qps_premier + qps_regular,
            ],
            [EVENTS, 1, 0, 1, 2],
        ]
        actual_tbody = response.context[QP_TABLE][TBODY]
        self.assertEqual(expected_tbody, actual_tbody)

    def test_top_finishes(self):
        player = PlayerFactory()
        ser_winner = EventPlayerResult.SingleEliminationResult.WINNER
        ser_quarter = EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST
        event1 = EventFactory(category=Event.Category.PREMIER)
        event2 = EventFactory(category=Event.Category.REGIONAL)
        EventPlayerResultFactory(
            points=10,
            player=player,
            event=event1,
            ranking=1,
            single_elimination_result=ser_quarter,
        )
        EventPlayerResultFactory(
            points=10,
            player=player,
            event=event2,
            ranking=2,
            single_elimination_result=ser_winner,
        )
        event3 = EventFactory(category=Event.Category.REGIONAL)
        EventPlayerResultFactory(points=10, player=player, event=event3, ranking=1)
        response = self.client.get(reverse("player_details", args=[player.id]))
        expected_top_finishes = [
            {
                THEAD: [
                    "",
                    Event.Category.PREMIER.label,
                    Event.Category.REGIONAL.label,
                ],
                TBODY: [
                    ["1st", 0, 1],
                    ["5th-8th", 1, 0],
                ],
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
