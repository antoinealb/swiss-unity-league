import datetime
from django.test import TestCase, Client
from icalendar import Calendar
from championship.models import Event
from championship.factories import EventFactory, AddressFactory, EventOrganizerFactory


class ICalFeedGetTest(TestCase):
    def test_ical_feed_get(self):
        """Basic smoke test that just exercises the view and checks that the
        event appears in it."""
        e = EventFactory(
            category=Event.Category.PREMIER, start_time=datetime.time(8, 0)
        )
        client = Client()
        resp = client.get("/events.ics")
        self.assertContains(resp, e.name)

    def test_ical_feed_exclude_regular(self):
        """Checks that SUL Regular events are not in the feed."""
        e = EventFactory(category=Event.Category.REGULAR)
        client = Client()
        resp = client.get("/events.ics")
        self.assertNotContains(resp, e.name)

    def test_includes_location(self):
        """Checks that we can add the address."""
        o = EventOrganizerFactory()
        a = AddressFactory(organizer=o, city="Foobar Town")
        e = EventFactory(category=Event.Category.PREMIER, organizer=o, address=a)
        resp = Client().get("/events.ics")
        calendar = Calendar.from_ical(resp.content)
        events = list(calendar.walk("VEVENT"))
        self.assertIn("Foobar Town", events[0]["LOCATION"])

    def test_ical_feed_all_events(self):
        e = EventFactory(category=Event.Category.REGULAR)
        client = Client()
        resp = client.get("/allevents.ics")
        calendar = Calendar.from_ical(resp.content)
        events = list(calendar.walk("VEVENT"))
        self.assertIn(e.name, events[0]["SUMMARY"])

    def test_ical_feed_only_premier(self):
        """Checks that there is an ical feed with only premier events"""
        e1 = EventFactory(category=Event.Category.REGULAR)
        e2 = EventFactory(category=Event.Category.REGIONAL)
        e3 = EventFactory(category=Event.Category.PREMIER)
        client = Client()
        resp = client.get("/premierevents.ics")

        calendar = Calendar.from_ical(resp.content)
        events = [str(c["SUMMARY"]) for c in calendar.walk("VEVENT")]

        self.assertEqual([f"[{e3.organizer.name}] {e3.name}"], events)
