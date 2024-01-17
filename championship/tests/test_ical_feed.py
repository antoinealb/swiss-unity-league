from django.test import TestCase, Client
from championship.factories import EventFactory


class ICalFeedGetTest(TestCase):
    def test_ical_feed_get(self):
        """Basic smoke test that just exercises the view and checks that the
        event appears in it."""
        e = EventFactory()
        client = Client()
        resp = client.get("/events.ics")
        self.assertContains(resp, e.name)
