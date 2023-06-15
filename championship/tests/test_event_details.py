from django.test import TestCase, Client
from django.urls import reverse
from championship.factories import *
from championship.models import *


class EventDetailTestCase(TestCase):
    """
    Tests how we can get an event's detail page.
    """

    def setUp(self):
        self.client = Client()
        credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(is_staff=True, **credentials)
        self.client.login(**credentials)

    def test_get_page(self):
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
        category = Event.Category.PREMIER
        event = EventFactory(category=category)

        # Create 18 results with a top8
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
        self.assertEqual(results[8].ranking, 9)
        self.assertEqual(
            results[0].single_elimination_result,
            EventPlayerResult.SingleEliminationResult.WINNER,
        )
        self.assertEqual(
            results[0].ranking_display,
            EventPlayerResult.SingleEliminationResult.WINNER.label,
        )
        self.assertEqual(
            results[8].ranking_display,
            "9th",
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
        event = EventFactory()
        resp = self.client.get(reverse("event_details", args=[event.id]))

        self.assertIn(
            reverse("admin:championship_event_change", args=[event.id]),
            resp.content.decode(),
        )

    def test_shows_link_for_top8(self):
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(category=Event.Category.REGIONAL, organizer=organizer)

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertIn(
            reverse("results_top8_add", args=[event.id]),
            resp.content.decode(),
        )

    def test_shows_no_link_top8_regular(self):
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(category=Event.Category.REGULAR, organizer=organizer)
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertNotIn(
            reverse("results_top8_add", args=[event.id]),
            resp.content.decode(),
        )

    def test_shows_link_delete_results(self):
        yesterday = datetime.date.today() - datetime.timedelta(1)
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(
            category=Event.Category.REGULAR, organizer=organizer, date=yesterday
        )
        for _ in range(3):
            EventPlayerResultFactory(event=event)
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertIn(
            reverse("event_clear_results", args=[event.id]),
            resp.content.decode(),
        )
