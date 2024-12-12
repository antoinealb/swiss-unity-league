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

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.forms import ValidationError
from django.urls import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)
from rest_framework.test import APITestCase

from parameterized import parameterized

from championship.factories import (
    AddressFactory,
    EventFactory,
    EventOrganizerFactory,
    RankedEventFactory,
    ResultFactory,
)
from championship.models import Event
from multisite.constants import GLOBAL_DOMAIN


class TestEventListAPI(APITestCase):
    def setUp(self):
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)

    def login(self):
        self.client.login(**self.credentials)

    def test_can_get_all_events(self):
        e1 = RankedEventFactory(
            description="Hello",
            start_time=datetime.time(hour=15),
            end_time=datetime.time(hour=17),
        )
        resp = self.client.get(reverse("events-list"))
        self.assertEqual(HTTP_200_OK, resp.status_code)

        resp = resp.json()
        want_organizer_url = "http://testserver" + reverse(
            "organizers-detail", args=[e1.organizer.id]
        )
        want = {
            "api_url": "http://testserver" + reverse("events-detail", args=[e1.id]),
            "name": e1.name,
            "date": e1.date.strftime("%Y-%m-%d"),
            "category": e1.category,
            "format": e1.format,
            "url": e1.url,
            "description": e1.description,
            "start_time": e1.start_time.strftime("%H:%M:%S"),
            "end_time": e1.end_time.strftime("%H:%M:%S"),
            "organizer": want_organizer_url,
            "results": [],
        }
        self.assertDictEqual(want, resp[0])

    def test_can_get_my_events_waiting_for_results(self):
        """Checks that I can get a series of events that can be used for event
        results."""
        # Just provide two events, we don't want to test the full logic of
        # Event.available_for_result_upload here.
        too_old = datetime.date(2023, 1, 1)
        RankedEventFactory(date=too_old, organizer=self.organizer)

        yesterday = datetime.date.today() - datetime.timedelta()
        event_good = RankedEventFactory(date=yesterday, organizer=self.organizer)

        event_with_results = RankedEventFactory(
            date=yesterday, organizer=self.organizer
        )
        for _ in range(8):
            ResultFactory(event=event_with_results)

        self.login()
        resp = self.client.get(reverse("events-need-results")).json()
        self.assertEqual(len(resp), 1)
        self.assertEqual(event_good.name, resp[0]["name"])

    def test_needs_to_be_logged_in_for_my_events(self):
        resp = self.client.get(reverse("events-need-results"))
        self.assertEqual(HTTP_401_UNAUTHORIZED, resp.status_code)


class TestEventCreate(APITestCase):
    def setUp(self):
        self.organizer = EventOrganizerFactory()
        self.data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "2022-12-25",
            "format": "LEGACY",
            "category": "PREMIER",
        }

    def login(self):
        self.client.force_login(self.organizer.user)

    def test_can_create_event(self):
        self.login()
        resp = self.client.post(reverse("events-list"), data=self.data, format="json")
        self.assertEqual(HTTP_201_CREATED, resp.status_code)
        self.assertEqual(1, Event.objects.count())

    def test_can_create_event_default_address(self):
        addr = AddressFactory(organizer=self.organizer)
        self.organizer.default_address = addr
        self.organizer.save()

        self.login()
        self.client.post(reverse("events-list"), data=self.data)
        self.assertEqual(Event.objects.all()[0].address, addr)

    def test_non_logged_in(self):
        resp = self.client.post(reverse("events-list"), data=self.data)
        self.assertEqual(HTTP_401_UNAUTHORIZED, resp.status_code)

    def test_event_delete(self):
        e = EventFactory(organizer=self.organizer)
        self.login()
        resp = self.client.delete(reverse("events-detail", args=[e.id]))
        self.assertEqual(HTTP_204_NO_CONTENT, resp.status_code)
        self.assertFalse(Event.objects.exists())

    def test_event_delete_not_allowed(self):
        e = EventFactory()  # Another organizer
        self.login()
        resp = self.client.delete(reverse("events-detail", args=[e.id]))
        self.assertEqual(HTTP_403_FORBIDDEN, resp.status_code)
        self.assertTrue(Event.objects.exists())

    def test_event_delete_old_with_results(self):
        """Checks that we are not allowed to change old results.

        SUL rules do not allow old events to be edited if they have results.
        See Event.can_be_edited.
        """
        e = RankedEventFactory(organizer=self.organizer, date=datetime.date(2023, 1, 1))
        for _ in range(10):
            ResultFactory(event=e)

        self.login()
        resp = self.client.delete(reverse("events-detail", args=[e.id]))
        self.assertEqual(HTTP_403_FORBIDDEN, resp.status_code)
        self.assertTrue(Event.objects.exists())

    def test_edit_event(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        e = RankedEventFactory(organizer=self.organizer, date=yesterday)
        self.login()
        data = {"name": "foobar"}
        resp = self.client.patch(reverse("events-detail", args=[e.id]), data=data)
        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.assertEqual(Event.objects.all()[0].name, "foobar")


class EventTypeCreateRestrictionTest(APITestCase):
    """Organizers require permission to create events of some categories."""

    def setUp(self):
        self.organizer = EventOrganizerFactory()
        self.client.force_login(self.organizer.user)
        self.data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "2022-12-25",
            "format": "LEGACY",
        }

    @parameterized.expand(
        [
            (Event.Category.OTHER, True),
            (Event.Category.REGULAR, True),
            (Event.Category.REGIONAL, True),
            (Event.Category.PREMIER, True),
            (Event.Category.NATIONAL, False),
            (Event.Category.QUALIFIER, False),
            (Event.Category.GRAND_PRIX, False),
        ]
    )
    def test_creating_some_event_types_not_allowed(self, category, is_allowed):
        self.data["category"] = category
        resp = self.client.post(reverse("events-list"), data=self.data, format="json")
        if is_allowed:
            self.assertEqual(HTTP_201_CREATED, resp.status_code)
        else:
            self.assertEqual(HTTP_400_BAD_REQUEST, resp.status_code)

    def test_premiers_not_allowed_on_global_site(self):
        self.organizer.site = Site.objects.get(domain=GLOBAL_DOMAIN)
        self.organizer.save()
        self.data["category"] = Event.Category.PREMIER
        with self.assertRaises(ValidationError):
            self.client.post(reverse("events-list"), data=self.data, format="json")


class EventTypeUpdateRestrictionTest(APITestCase):
    """Organizers require permission to update events of some categories."""

    def setUp(self):
        self.event = EventFactory(
            date=datetime.date.today(),
            category=Event.Category.OTHER,
        )
        self.client.force_login(self.event.organizer.user)
        self.data = {
            "name": "Test Event",
        }

    @parameterized.expand(
        [
            (Event.Category.REGULAR, True),
            (Event.Category.REGIONAL, True),
            (Event.Category.PREMIER, True),
            (Event.Category.NATIONAL, False),
            (Event.Category.QUALIFIER, False),
            (Event.Category.GRAND_PRIX, False),
        ]
    )
    def test_edit_to_some_event_type_not_allowed(self, category, is_allowed):
        self.data["category"] = category
        resp = self.client.patch(
            reverse("events-detail", args=[self.event.id]), data=self.data
        )
        if is_allowed:
            self.assertEqual(HTTP_200_OK, resp.status_code)
        else:
            self.assertEqual(HTTP_400_BAD_REQUEST, resp.status_code)

    @parameterized.expand(
        [
            (Event.Category.REGULAR, True),
            (Event.Category.REGIONAL, True),
            (Event.Category.PREMIER, True),
            (Event.Category.NATIONAL, False),
            (Event.Category.QUALIFIER, False),
            (Event.Category.GRAND_PRIX, False),
        ]
    )
    def test_edit_away_from_event_type_not_allowed(self, category, is_allowed):
        self.event.category = category
        self.event.save()
        self.data["category"] = Event.Category.OTHER
        resp = self.client.patch(
            reverse("events-detail", args=[self.event.id]), data=self.data
        )
        if is_allowed:
            self.assertEqual(HTTP_200_OK, resp.status_code)
        else:
            self.assertEqual(HTTP_400_BAD_REQUEST, resp.status_code)

    def test_edit_event_type_to_same_type_is_allowed(self):
        self.event.category = Event.Category.GRAND_PRIX
        self.event.save()
        self.data["category"] = Event.Category.GRAND_PRIX
        resp = self.client.patch(
            reverse("events-detail", args=[self.event.id]), data=self.data
        )
        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.event.refresh_from_db()
        self.event.name = self.data["name"]
