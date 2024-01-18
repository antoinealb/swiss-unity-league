import datetime
from django.test import TestCase, Client
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
        self.assertContains(resp, "Foobar Town")
