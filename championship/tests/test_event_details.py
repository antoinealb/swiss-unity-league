from django.test import TestCase, Client
from django.urls import reverse
from championship.factories import *
from championship.models import *


class EventDetailTestCase(TestCase):
    """
    Tests how we can get an event's detail page.
    """

    def test_get_page(self):
        self.client = Client()

        event = EventFactory(category=Event.Category.PREMIER)
        player = PlayerFactory()
        EventPlayerResult.objects.create(
            points=10, player=player, event=event, ranking=1
        )

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertIn(event.name, resp.content.decode())
        self.assertIn(player.name, resp.content.decode())

        self.assertEqual(resp.context_data["results"][0].points, 10)
        self.assertEqual(resp.context_data["results"][0].qps, (10 + 3) * 6)

    def test_get_result_with_top_8(self):
        self.client = Client()

        event = EventFactory(category=Event.Category.PREMIER)
        player = PlayerFactory()

        # Create 10 results with a top8
        results = (
            [
                EventPlayerResult.SingleEliminationResult.WINNER,
                EventPlayerResult.SingleEliminationResult.FINALIST,
            ]
            + [EventPlayerResult.SingleEliminationResult.SEMI_FINALIST] * 2
            + [EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST] * 4
            + [None] * 10  # outside of top8
        )

        for i, r in enumerate(results):
            EventPlayerResult.objects.create(
                points=10,
                player=PlayerFactory(),
                event=event,
                ranking=i + 1,
                single_elimination_result=r,
            )

        resp = self.client.get(reverse("event_details", args=[event.id]))
        results = resp.context_data["results"]
        top8_results = resp.context_data["top_results"]
        self.assertEqual(results[0].ranking, 9)
        self.assertEqual(
            top8_results[0].single_elimination_result,
            EventPlayerResult.SingleEliminationResult.WINNER,
        )

    def test_escapes_content_description(self):
        """
        Checks that we correctly strip tags unknown tags.
        """
        descr = """
        <b>Bold</b>
        <script>alert()</script>
        """
        want = """
        <b>Bold</b>
        alert()
        """
        event = EventFactory(description=descr)
        self.assertEqual(want, event.description)

    def test_shows_link_for_admin_page(self):
        client = Client()
        credentials = dict(username="test", password="test")
        user = User.objects.create_user(is_staff=True, **credentials)
        client.login(**credentials)

        event = EventFactory()
        resp = client.get(reverse("event_details", args=[event.id]))

        self.assertIn(
            reverse("admin:championship_event_change", args=[event.id]),
            resp.content.decode(),
        )

    def test_shows_link_for_top8(self):
        client = Client()
        credentials = dict(username="test", password="test")
        user = User.objects.create_user(is_staff=True, **credentials)
        organizer = EventOrganizerFactory(user=user)
        client.login(**credentials)

        event = EventFactory(category=Event.Category.REGIONAL, organizer=organizer)
        resp = client.get(reverse("event_details", args=[event.id]))
        self.assertIn(
            reverse("results_top8_add", args=[event.id]),
            resp.content.decode(),
        )

    def test_shows_no_link_top8_regular(self):
        client = Client()
        credentials = dict(username="test", password="test")
        user = User.objects.create_user(**credentials)
        client.login(**credentials)
        organizer = EventOrganizerFactory(user=user)

        event = EventFactory(category=Event.Category.REGULAR, organizer=organizer)
        resp = client.get(reverse("event_details", args=[event.id]))
        self.assertNotIn(
            reverse("results_top8_add", args=[event.id]),
            resp.content.decode(),
        )
