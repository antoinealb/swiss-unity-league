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
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK

from parameterized import parameterized

from championship.factories import (
    EventFactory,
    EventOrganizerFactory,
    RecurringEventFactory,
    ResultFactory,
)
from championship.models import Address, Event


class EventCreationTestCase(TestCase):
    """
    Tests for the feature that create new events for tournament organizers.
    """

    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)

    def login(self):
        self.client.login(**self.credentials)

    def test_link_not_shown_to_anonymous_users(self):
        response = self.client.get("/")

        self.assertNotIn(
            reverse("events_create"),
            response.content.decode(),
            "Anonymous users should not see the link to the event create page.",
        )

    def test_link_not_shown_if_no_to(self):
        """
        Checks that we don't show the link to accounts that are not TO accounts.
        """
        self.login()
        response = self.client.get("/")
        self.assertNotIn(
            reverse("events_create"),
            response.content.decode(),
            "Non TOs should not have the link",
        )

    def test_link_shown_when_authenticated(self):
        self.login()
        EventOrganizerFactory(user=self.user)
        response = self.client.get("/")
        self.assertIn(
            reverse("events_create"),
            response.content.decode(),
            "Logged in users should get a link to creating events",
        )

    def test_create_event(self):
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "11/26/2022",
            "format": "LEGACY",
            "category": "PREMIER",
        }
        self.login()
        EventOrganizerFactory(user=self.user)

        self.client.post(reverse("events_create"), data=data)

        event = Event.objects.all()[0]

        self.assertEqual(event.name, "Test Event")
        self.assertEqual(event.url, "https://test.example")
        self.assertEqual(event.date, datetime.date(2022, 11, 26))
        self.assertEqual(event.format, event.Format.LEGACY)
        self.assertEqual(event.category, event.Category.PREMIER)

    def test_create_event_redirects(self):
        """
        Checks that once the event is created, we get redirected to it.
        """
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "11/26/2022",
            "format": "LEGACY",
            "category": "PREMIER",
        }
        self.login()
        EventOrganizerFactory(user=self.user)

        resp = self.client.post(reverse("events_create"), data=data, follow=True)

        event = Event.objects.all()[0]

        self.assertRedirects(resp, reverse("event_details", args=[event.id]))

    def test_create_event_redirects_schedule_series(self):
        """
        Checks we can also create an event and go to the schedule series page.
        """
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "11/26/2022",
            "format": "LEGACY",
            "category": "PREMIER",
            "submit_type": "schedule_series",
        }
        self.login()
        EventOrganizerFactory(user=self.user)

        resp = self.client.post(reverse("events_create"), data=data, follow=True)

        event = Event.objects.all()[0]

        self.assertRedirects(resp, reverse("recurring_event_create", args=[event.id]))

    def test_update_event(self):
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": datetime.date.today().strftime("%m/%d/%Y"),
            "format": "LEGACY",
            "category": "PREMIER",
        }
        self.login()
        to = EventOrganizerFactory(user=self.user)

        self.client.post(reverse("events_create"), data=data)

        data["name"] = "Updated Event"
        data["decklists_url"] = "http://mtgtop8.com"

        event = Event.objects.all()[0]

        self.client.post(reverse("event_update", args=[event.id]), data=data)

        event = Event.objects.get(pk=event.id)

        self.assertEqual(event.name, data["name"])
        self.assertEqual(event.decklists_url, data["decklists_url"])
        self.assertEqual(event.organizer, to)

    def test_update_event_from_someone_else(self):
        other_to = EventOrganizerFactory()
        event = EventFactory(organizer=other_to, date=datetime.date.today())

        # Try to change an event ran by the other TO
        EventOrganizerFactory(user=self.user)
        self.login()
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": datetime.date.today().strftime("%m/%d/%Y"),
            "format": "LEGACY",
            "category": "PREMIER",
        }

        resp = self.client.post(reverse("event_update", args=[event.id]), data=data)

        self.assertEqual(403, resp.status_code)

    def test_update_link_shown_to_organizer(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(organizer=to, date=datetime.date.today())

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertNotIn(
            reverse("event_update", args=[event.id]), resp.content.decode()
        )

        self.login()

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertIn(reverse("event_update", args=[event.id]), resp.content.decode())

    def test_get_update_page(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(organizer=to, date=datetime.date.today())

        self.login()
        resp = self.client.get(reverse("event_update", args=[event.id]))
        self.assertEqual(200, resp.status_code)

    def test_update_old_events_is_forbidden(self):
        to = EventOrganizerFactory(user=self.user)
        old_date = datetime.date.today() - datetime.timedelta(days=32)
        event = EventFactory(organizer=to, date=old_date)

        self.login()
        resp = self.client.get(reverse("event_update", args=[event.id]))
        self.assertEqual(403, resp.status_code)

    def test_update_making_event_old_is_forbidden(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(organizer=to, date=datetime.date.today())

        self.login()
        old_date = datetime.date.today() - datetime.timedelta(days=32)
        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": old_date.strftime("%m/%d/%Y"),
            "format": "LEGACY",
            "category": "PREMIER",
        }

        resp = self.client.post(reverse("event_update", args=[event.id]), data=data)
        self.assertEqual(200, resp.status_code)
        event = Event.objects.get(pk=event.id)
        self.assertEqual(datetime.date.today(), event.date)

    def test_get_delete_page(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(organizer=to)

        self.login()
        resp = self.client.get(reverse("event_delete", args=[event.id]))
        self.assertEqual(resp.status_code, HTTP_200_OK)

    def test_delete_event(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(organizer=to, date=datetime.date.today())

        self.login()
        self.client.post(reverse("event_delete", args=[event.id]))

        self.assertEqual(Event.objects.count(), 0)

    def test_delete_old_event(self):
        to = EventOrganizerFactory(user=self.user)
        event = EventFactory(
            organizer=to, date=datetime.date.today() - datetime.timedelta(days=32)
        )

        # Old event with results cannot be deleted
        epr = ResultFactory(event=event)
        self.login()
        self.client.post(reverse("event_delete", args=[event.id]))
        self.assertEqual(Event.objects.count(), 1)

        # Old event without results can be deleted
        epr.delete()
        self.client.post(reverse("event_delete", args=[event.id]))
        self.assertEqual(Event.objects.count(), 0)

    def test_delete_event_for_another_to(self):
        EventOrganizerFactory(user=self.user)
        event = EventFactory()  # created for another to

        self.login()
        resp = self.client.post(reverse("event_delete", args=[event.id]))
        self.assertEqual(403, resp.status_code)
        self.assertEqual(Event.objects.count(), 1)

    def test_default_address_is_initial(self):
        self.login()
        to = EventOrganizerFactory(user=self.user)
        response = self.client.get(reverse("events_create"))
        initial_address = response.context["form"].initial["address"]
        self.assertEqual(to.default_address.id, initial_address)

    def test_create_event_form_without_any_address(self):
        self.login()
        EventOrganizerFactory(user=self.user)
        Address.objects.all().delete()
        self.client.get(reverse("events_create"))

    def test_initial_address_not_overwritten_by_default_address(self):
        to = EventOrganizerFactory(user=self.user)
        not_default_address = to.addresses.all()[1]
        event = EventFactory(
            address=not_default_address, organizer=to, date=datetime.date.today()
        )
        self.login()
        response = self.client.get(reverse("event_update", args=[event.id]))
        self.assertEqual(200, response.status_code)
        initial_address = response.context["form"].initial["address"]
        self.assertNotEqual(not_default_address, to.default_address)
        self.assertEqual(not_default_address.id, initial_address)

    @parameterized.expand(
        [
            ("events_create", False),
            ("event_update", True),
            ("event_copy", True),
        ]
    )
    def test_update_event_contains_only_organizer_addresses(self, view_name, has_id):
        to = EventOrganizerFactory(user=self.user)
        # Create another TO with addresses and check that both have 3 addresses
        for current_to in [to, EventOrganizerFactory()]:
            self.assertEqual(3, current_to.addresses.count())
        event = EventFactory(organizer=to, date=datetime.date.today())
        self.login()
        response = self.client.get(
            reverse(view_name, args=[event.id]) if has_id else reverse(view_name)
        )
        self.assertEqual(200, response.status_code)
        form_addresses = response.context["form"].fields["address"].queryset
        self.assertEqual(to.addresses.count(), form_addresses.count())
        for address in form_addresses:
            self.assertIn(address, to.addresses.all())


class EventCopyTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)

    def login(self):
        self.client.login(**self.credentials)

    def test_current_event_in_context(self):
        self.login()
        event = EventFactory(organizer=self.organizer)
        r = self.client.get(reverse("event_copy", args=[event.id]))
        self.assertEqual(event, r.context["event"])

    def test_copy_event(self):
        self.login()
        event = EventFactory()

        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "11/26/2022",
            "format": "LEGACY",
            "category": "PREMIER",
        }

        self.client.post(reverse("event_copy", args=[event.id]), data=data)

        self.assertEqual(2, Event.objects.count())

    def test_copy_button_shown(self):
        self.login()
        event = EventFactory(organizer=self.organizer)

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(resp, reverse("event_copy", args=[event.id]))

    def test_initial_address_not_overwritten_by_default_address(self):
        self.login()
        not_default_address = self.organizer.get_addresses()[1]
        event = EventFactory(address=not_default_address, organizer=self.organizer)
        response = self.client.get(reverse("event_copy", args=[event.id]))
        initial_address = response.context["form"].initial["address"]
        self.assertNotEqual(not_default_address, self.organizer.default_address)
        self.assertEqual(not_default_address.id, initial_address)

    def test_copy_event_with_recurring_event(self):
        self.login()
        recurring_event = RecurringEventFactory()
        event = EventFactory(recurring_event=recurring_event)

        data = {
            "name": "Test Event",
            "url": "https://test.example",
            "date": "11/26/2022",
            "format": "LEGACY",
            "category": "PREMIER",
        }

        self.client.post(reverse("event_copy", args=[event.id]), data=data)
        events = Event.objects.all()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].recurring_event, recurring_event)
        self.assertIsNone(events[1].recurring_event)
