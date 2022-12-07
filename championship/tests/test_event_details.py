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
