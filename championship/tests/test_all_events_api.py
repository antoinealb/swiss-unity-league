from django.test import TestCase, Client
from django.urls import reverse
from championship.factories import *
from championship.models import *

TEST_SERVER = "http://testserver"

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
                "details_url": TEST_SERVER
                + reverse("event_details", args=[a.id]),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[a.id]),
            }
        ]
        self.assertEqual(want, resp.json())

    def test_get_all_past_events(self):
        eo = EventOrganizerFactory(name="Test TO")
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        a = EventFactory(
            organizer=eo,
            date=yesterday,
            format=Event.Format.LEGACY,
            category=Event.Category.PREMIER,
        )
        resp = Client().get(reverse("past-events-list"))
        want = [
            {
                "name": a.name,
                "date": yesterday.strftime("%d.%m.%Y"),
                "organizer": eo.name,
                "format": "Legacy",
                "category": "SUL Premier",
                "details_url": TEST_SERVER
                + reverse("event_details", args=[a.id]),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[a.id]),
            }
        ]
        self.assertEqual(want, resp.json())


class FormatsApiTestCase(TestCase):
    def test_get_all_formats(self):
        resp = Client().get(reverse("formats-list"))
        want = sorted(Event.Format.labels)
        self.assertEqual(want, resp.json())
