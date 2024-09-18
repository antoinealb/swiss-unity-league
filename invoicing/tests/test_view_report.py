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

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from parameterized import parameterized

from championship.factories import EventFactory, ResultFactory
from championship.models import Event
from championship.season import SEASON_2024, SEASON_LIST
from invoicing.factories import InvoiceFactory
from invoicing.models import fee_for_event
from invoicing.views import Report


class ReportRenderingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials, is_superuser=True)
        self.client.force_login(self.user)

    def test_get_empty_report(self):
        # We don't have any results yet
        resp = self.client.get(reverse("invoice_report"))
        self.assertEqual(HTTP_200_OK, resp.status_code)

    def test_get_image(self):
        for s in SEASON_LIST:
            event = EventFactory(date=s.start_date, category=Event.Category.REGIONAL)
            for _ in range(10):
                ResultFactory(event=event)

        resp = self.client.get(reverse("invoice_report"))
        self.assertIn("revenue_plot", resp.context)

        self.assertTrue(
            resp.context["revenue_plot"].startswith(
                "data:image/png;charset=utf-8;base64,"
            )
        )

    def test_image_encode(self):
        r = Report()
        data = r.encode_image(b"hello")
        self.assertEqual(data, "data:image/png;charset=utf-8;base64,aGVsbG8=")

    @parameterized.expand(
        [
            (Event.Category.PREMIER,),
            (Event.Category.REGIONAL,),
        ]
    )
    def test_points_for_season(self, category):
        dates = [
            SEASON_2024.start_date + datetime.timedelta(days=i) for i in range(1, 10)
        ]
        events = [EventFactory(date=date, category=category) for date in dates]

        for event in events:
            for _ in range(10):
                ResultFactory(event=event, single_elimination_result=None)

        # All events will have the same fees.
        price_per_event = fee_for_event(Event.objects.all()[0])

        want = [(i, price_per_event * i) for i in range(1, 10)]
        got = list(Report().data_points_for_season(SEASON_2024))
        self.assertEqual(want, got)

    @parameterized.expand(
        [
            (Event.Category.PREMIER,),
            (Event.Category.REGIONAL,),
        ]
    )
    def test_map_event_discount_takes_first_event_always(self, category):
        invoice = InvoiceFactory(
            start_date=SEASON_2024.start_date,
            end_date=SEASON_2024.end_date,
            discount=100,
        )
        dates = [
            SEASON_2024.start_date + datetime.timedelta(days=i) for i in range(1, 10)
        ]
        events = [
            EventFactory(
                date=date, category=category, organizer=invoice.event_organizer
            )
            for date in dates
        ]
        discounts = list(Report().map_discounts_to_event(SEASON_2024))
        want = [(events[0], 100)]
        self.assertEqual(want, discounts)

    def test_map_event_discount_prefers_premier(self):
        """When we have both a Premier and a Regional in the invoicing period,
        we would like the discount to be considered on the premier."""
        invoice = InvoiceFactory(
            start_date=SEASON_2024.start_date,
            end_date=SEASON_2024.end_date,
            discount=100,
        )
        EventFactory(
            date=invoice.start_date,
            category=Event.Category.REGIONAL,
            organizer=invoice.event_organizer,
        )
        want_event = EventFactory(
            date=invoice.end_date,
            category=Event.Category.PREMIER,
            organizer=invoice.event_organizer,
        )

        discounts = list(Report().map_discounts_to_event(SEASON_2024))
        want = [(want_event, 100)]
        self.assertEqual(want, discounts)

    def test_discount_is_applied_to_data_points(self):
        """Checks that the discount is taken into account in the plot."""
        invoice = InvoiceFactory(
            start_date=SEASON_2024.start_date,
            end_date=SEASON_2024.end_date,
            discount=100,
        )
        event = EventFactory(
            date=invoice.start_date,
            category=Event.Category.REGIONAL,
            organizer=invoice.event_organizer,
        )

        for _ in range(10):
            ResultFactory(event=event, single_elimination_result=None)

        want = [(0, fee_for_event(event) - invoice.discount)]
        got = list(Report().data_points_for_season(SEASON_2024))
        self.assertEqual(want, got)


class ReportPermissionTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.report_url = reverse("invoice_report")

    def test_anonymous_user_cannot_access(self):
        # No login
        login_url = reverse("login")
        want_redirect = f"{login_url}?next={self.report_url}"

        resp = self.client.get(self.report_url)
        self.assertRedirects(
            resp,
            want_redirect,
            msg_prefix="Access to financial report should be denied",
        )

    def test_logged_in_no_permission_cannot_access(self):
        # Login, no permission
        self.client.force_login(self.user)
        resp = self.client.get(self.report_url)
        self.assertEqual(HTTP_403_FORBIDDEN, resp.status_code)

    def test_logged_in_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_invoice"))
        self.client.force_login(self.user)
        resp = self.client.get(self.report_url)
        self.assertEqual(HTTP_200_OK, resp.status_code)

    def test_does_not_have_report_url_in_menu(self):
        self.client.force_login(self.user)
        resp = self.client.get("/")
        self.assertNotIn(self.report_url, resp.content.decode())

    def test_logged_in_gets_it_shown_in_menu(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_invoice"))
        self.client.force_login(self.user)
        resp = self.client.get("/")
        self.assertIn(self.report_url, resp.content.decode())
