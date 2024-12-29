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

from django.test import TestCase
from django.urls import reverse

from championship.factories import AddressFactory, EventFactory, EventOrganizerFactory
from championship.models import Address, Event
from championship.seasons.definitions import SEASON_2023

TEST_SERVER = "http://testserver"


class EventApiTestCase(TestCase):
    def test_get_all_past_events(self):
        eo = EventOrganizerFactory(name="Test TO")
        eo.default_address = AddressFactory(
            region=Address.Region.BERN,
            country="CH",
            organizer=eo,
        )
        eo.save()
        event_address = AddressFactory(
            region=Address.Region.AARGAU, country="DE", organizer=eo
        )
        base_date = datetime.date(2023, 1, 1)
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
        resp = self.client.get(
            reverse("past-events-list", kwargs={"slug": SEASON_2023.slug})
        )
        want = [
            {
                "name": a.name,
                "date": older_date.strftime("%a, %d.%m.%Y"),
                "time": "10:00 - 19:00",
                "startDateTime": "2023-01-03T10:00:00",
                "endDateTime": "2023-01-03T19:00:00",
                "organizer": eo.name,
                "format": "Legacy",
                "locationName": event_address.location_name,
                "seoAddress": event_address.get_seo_address(),
                "shortAddress": f", {event_address.city}, {event_address.get_region_display()}, {event_address.get_country_display()}",
                "region": "Aargau",
                "distance_km": None,
                "category": Event.Category.REGULAR.label,
                "details_url": TEST_SERVER + reverse("event_details", args=[a.id]),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[eo.id]),
                "icon_url": "/static/types/icons/regular.png",
            },
            {
                "name": b.name,
                "date": younger_date.strftime("%a, %d.%m.%Y"),
                "time": "12:00 - 14:00",
                "startDateTime": "2023-01-02T12:00:00",
                "endDateTime": "2023-01-02T14:00:00",
                "organizer": eo.name,
                "format": "Modern",
                "locationName": eo.default_address.location_name,
                "seoAddress": eo.default_address.get_seo_address(),
                "shortAddress": f", {eo.default_address.city}, {eo.default_address.get_region_display()}",
                "region": "Bern",
                "distance_km": None,
                "category": Event.Category.REGIONAL.label,
                "details_url": TEST_SERVER + reverse("event_details", args=[b.id]),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[eo.id]),
                "icon_url": "/static/types/icons/regional.png",
            },
        ]
        self.assertEqual(want, resp.json())


class FutureEventsView(TestCase):
    def test_get_all_future_events(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        event = EventFactory(
            date=tomorrow,
            format=Event.Format.LEGACY,
            category=Event.Category.PREMIER,
        )
        resp = self.client.get(reverse("events"))
        address = event.organizer.default_address
        want = [
            {
                "name": event.name,
                "date": tomorrow.strftime("%a, %d.%m.%Y"),
                "time": "",
                "startDateTime": tomorrow.isoformat(),
                "endDateTime": "",
                "organizer": event.organizer.name,
                "format": "Legacy",
                "locationName": address.location_name,
                "seoAddress": address.get_seo_address(),
                "shortAddress": f", {address.city}, {address.get_region_display()}, {address.get_country_display()}",
                "region": address.get_region_display(),
                "distance_km": None,
                "category": Event.Category.PREMIER.label,
                "details_url": TEST_SERVER + event.get_absolute_url(),
                "organizer_url": TEST_SERVER
                + reverse("organizer_details", args=[event.id]),
                "icon_url": "/static/types/icons/premier.png",
            }
        ]
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(want, resp.context["events"])

    def test_future_events_are_ordered_by_date(self):
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        e1 = EventFactory(date=tomorrow)
        e2 = EventFactory(date=today)
        got_events = self.client.get(reverse("events")).context["events"]
        want_events = [e2, e1]
        self.assertEqual(
            [p["name"] for p in got_events],
            [p.name for p in want_events],
            "Events should be ordered by date",
        )
