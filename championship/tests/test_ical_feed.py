# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

from django.test import Client, TestCase

from icalendar import Calendar

from championship.factories import AddressFactory, EventFactory, EventOrganizerFactory
from championship.models import Event


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
