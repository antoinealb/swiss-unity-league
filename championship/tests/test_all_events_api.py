from django.test import TestCase, Client
from django.urls import reverse
from championship.factories import *
from championship.models import *


class EventApiTestCase(TestCase):
    def test_get_all_future_events(self):
        eo = EventOrganizerFactory(name="Test TO")
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        a = EventFactory(
            organizer=eo,
            date=tomorrow,
            format=Event.Format.LEGACY,
            category=Event.Category.PREMIER,
        )
        resp = Client().get(reverse("future-events-list"))
        want = [
            {
                "name": a.name,
                "date": tomorrow.strftime("%d.%m.%Y"),
                "organizer": eo.name,
                "format": "Legacy",
                "category": "SUL Premier",
                "details_url": "http://testserver"
                + reverse("event_details", args=[a.id]),
            }
        ]
        self.assertEqual(want, resp.json())
