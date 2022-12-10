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
        EventPlayerResult.objects.create(points=10, player=player, event=event)

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertIn(event.name, resp.content.decode())
        self.assertIn(player.name, resp.content.decode())

        self.assertEqual(resp.context_data["results"][0].points, 10)
        self.assertEqual(resp.context_data["results"][0].qps, (10 + 3) * 6)

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
