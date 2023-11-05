from django.test import TestCase, Client
from django.urls import reverse
from championship.factories import *
from championship.models import *

TEST_SERVER = "http://testserver"


class EventApiTestCase(TestCase):
    def test_get_all_future_events(self):
        eo = EventOrganizerFactory(name="Test TO", addresses=[])
        eo.default_address = AddressFactory(
            region=Address.Region.BERN,
            country=Address.Country.SWITZERLAND,
            organizer=eo,
        )
        eo.save()
        event_address = AddressFactory(
            region=Address.Region.AARGAU, country=Address.Country.GERMANY, organizer=eo
        )
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        in_2_days = datetime.date.today() + datetime.timedelta(days=2)
        a = EventFactory(
            organizer=eo,
            date=tomorrow,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(19, 0),
            format=Event.Format.LEGACY,
            category=Event.Category.PREMIER,
            address=event_address,
        )
        b = EventFactory(
            organizer=eo,
            date=in_2_days,
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
            format=Event.Format.MODERN,
            category=Event.Category.REGIONAL,
        )
        resp = Client().get(reverse("future-events-list"))
        want = [
            {
                "name": a.name,
                "date": tomorrow.strftime("%a, %d.%m.%Y"),
                "time": "10:00 - 19:00",
                "organizer": eo.name,
                "format": "Legacy",
                "address": f", {event_address.city}, {event_address.get_region_display()}, {event_address.get_country_display()}",
                "category": "SUL Premier",
                "details_url": TEST_SERVER + reverse("event_details", args=[a.id]),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[eo.id]),
            },
            {
                "name": b.name,
                "date": in_2_days.strftime("%a, %d.%m.%Y"),
                "time": "12:00 - 14:00",
                "organizer": eo.name,
                "format": "Modern",
                "address": f", {eo.default_address.city}, {eo.default_address.get_region_display()}",
                "category": "SUL Regional",
                "details_url": TEST_SERVER + reverse("event_details", args=[b.id]),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[eo.id]),
            },
        ]
        self.assertEqual(want, resp.json())

    def test_get_all_past_events(self):
        eo = EventOrganizerFactory(name="Test TO", addresses=[])
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
                "date": yesterday.strftime("%a, %d.%m.%Y"),
                "time": "",
                "organizer": eo.name,
                "format": "Legacy",
                "address": "",
                "category": "SUL Premier",
                "details_url": TEST_SERVER + reverse("event_details", args=[a.id]),
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
