import datetime
from django.test import TestCase, Client
from django.urls import reverse
from icalendar import Calendar
from championship.models import Event
from championship.factories import EventFactory, AddressFactory, EventOrganizerFactory


class ICalFeedGetTest(TestCase):
    def get_ical_feed(self, url):
        """Gets an iCal feed by URL and parse it.

        We specifically get an URL rather than reverse() it, as that URL is
        part of UnityLeague's API contract. It will be stored by others (like
        google calendar) and should never be changed."""
        client = Client()
        resp = client.get(url)
        self.assertEqual(200, resp.status_code)
        calendar = Calendar.from_ical(resp.content)
        return list(calendar.walk("VEVENT"))

    def test_ical_feed_get(self):
        """Basic smoke test that just exercises the view and checks that the
        event appears in it."""
        e = EventFactory(
            category=Event.Category.PREMIER, start_time=datetime.time(8, 0)
        )
        events = self.get_ical_feed("/events.ics")

        events = [str(c["SUMMARY"]) for c in events]
        self.assertEqual([f"[{e.organizer.name}] {e.name}"], events)

    def test_ical_feed_exclude_regular(self):
        """Checks that SUL Regular events are not in the feed."""
        EventFactory(category=Event.Category.REGULAR)
        events = self.get_ical_feed("/events.ics")
        self.assertEqual([], events)

    def test_includes_location(self):
        """Checks that we can add the address."""
        o = EventOrganizerFactory()
        a = AddressFactory(organizer=o, city="Foobar Town")
        EventFactory(category=Event.Category.PREMIER, organizer=o, address=a)
        events = self.get_ical_feed("/events.ics")
        self.assertIn("Foobar Town", events[0]["LOCATION"])

    def test_ical_feed_all_events(self):
        e = EventFactory(category=Event.Category.REGULAR)
        events = self.get_ical_feed("/allevents.ics")
        self.assertIn(e.name, events[0]["SUMMARY"])

    def test_ical_feed_only_premier(self):
        """Checks that there is an ical feed with only premier events"""
        EventFactory(category=Event.Category.REGULAR)
        EventFactory(category=Event.Category.REGIONAL)
        e = EventFactory(category=Event.Category.PREMIER)
        events = self.get_ical_feed("/premierevents.ics")
        events = [str(c["SUMMARY"]) for c in events]
        self.assertEqual([f"[{e.organizer.name}] {e.name}"], events)

    def test_get_ical_page(self):
        """Checks that the information page for ical integration exists."""
        client = Client()
        resp = client.get(reverse("info_ical"))
        self.assertEqual(200, resp.status_code)
