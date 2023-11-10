from django.test import TestCase, Client
from django.urls import reverse
from championship.factories import *
from championship.models import *

TEST_SERVER = "http://testserver"


class EventApiTestCase(TestCase):
    def test_get_all_past_events(self):
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
        base_date = datetime.date(2020, 1, 1)
        older_date = base_date + datetime.timedelta(days=2)
        younger_date = base_date + datetime.timedelta(days=1)
        a = EventFactory(
            organizer=eo,
            date=older_date,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(19, 0),
            format=Event.Format.LEGACY,
            category=Event.Category.REGULAR,
            address=event_address,
        )
        b = EventFactory(
            organizer=eo,
            date=younger_date,
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
            format=Event.Format.MODERN,
            category=Event.Category.REGIONAL,
        )
        resp = Client().get(reverse("past-events-list"))
        want = [
            {
                "name": a.name,
                "date": older_date.strftime("%a, %d.%m.%Y"),
                "time": "10:00 - 19:00",
                "startDateTime": "2020-01-03T10:00:00",
                "endDateTime": "2020-01-03T19:00:00",
                "organizer": eo.name,
                "format": "Legacy",
                "locationName": event_address.location_name,
                "seoAddress": event_address.get_seo_address(),
                "shortAddress": f", {event_address.city}, {event_address.get_region_display()}, {event_address.get_country_display()}",
                "region": "Aargau",
                "category": "SUL Regular",
                "details_url": TEST_SERVER + reverse("event_details", args=[a.id]),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[eo.id]),
                "icon_url": "/static/types/icons/regular.png",
            },
            {
                "name": b.name,
                "date": younger_date.strftime("%a, %d.%m.%Y"),
                "time": "12:00 - 14:00",
                "startDateTime": "2020-01-02T12:00:00",
                "endDateTime": "2020-01-02T14:00:00",
                "organizer": eo.name,
                "format": "Modern",
                "locationName": eo.default_address.location_name,
                "seoAddress": eo.default_address.get_seo_address(),
                "shortAddress": f", {eo.default_address.city}, {eo.default_address.get_region_display()}",
                "region": "Bern",
                "category": "SUL Regional",
                "details_url": TEST_SERVER + reverse("event_details", args=[b.id]),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[eo.id]),
                "icon_url": "/static/types/icons/regional.png",
            },
        ]
        self.assertEqual(want, resp.json())

    def test_get_all_future_events(self):
        eo = EventOrganizerFactory(name="Test TO", addresses=[])
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
                "date": tomorrow.strftime("%a, %d.%m.%Y"),
                "time": "",
                "startDateTime": tomorrow.isoformat(),
                "endDateTime": "",
                "organizer": eo.name,
                "format": "Legacy",
                "locationName": "",
                "seoAddress": "",
                "shortAddress": "",
                "region": "",
                "category": "SUL Premier",
                "details_url": TEST_SERVER + reverse("event_details", args=[a.id]),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[a.id]),
                "icon_url": "/static/types/icons/premier.png",
            }
        ]
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(want, resp.json())


class FormatsApiTestCase(TestCase):
    def test_get_all_formats(self):
        resp = Client().get(reverse("formats-list"))
        want = sorted(Event.Format.labels)
        self.assertEqual(want, resp.json())
