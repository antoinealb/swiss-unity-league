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
import unittest
from subprocess import DEVNULL, check_call

from django.contrib.auth.models import Permission, User
from django.core.files.base import ContentFile
from django.test import Client, TestCase, tag
from django.urls import reverse

from championship.factories import EventFactory, EventOrganizerFactory, ResultFactory
from championship.models import Event
from invoicing.factories import InvoiceFactory


def has_latex():
    try:
        check_call(["lualatex", "--help"], stdout=DEVNULL, stderr=DEVNULL)
    except FileNotFoundError:
        return False
    return True


@tag("latex")
@unittest.skipUnless(has_latex(), "Can only run if lualatex is available")
class InvoiceRenderingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.to = EventOrganizerFactory(user=self.user)
        self.login()

    def login(self):
        self.client.login(**self.credentials)

    def test_get_invoice(self):
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        invoice = InvoiceFactory(
            event_organizer=self.to, start_date=yesterday, end_date=today
        )
        resp = self.client.get(reverse("invoice_get", args=(invoice.id,)))
        self.assertEqual(200, resp.status_code)

    def test_get_invoice_of_another_to(self):
        # Create an invoice belonging to another TO
        invoice = InvoiceFactory()
        resp = self.client.get(reverse("invoice_get", args=(invoice.id,)))
        self.assertEqual(404, resp.status_code)

    def test_staff_can_view_all_invoices(self):
        perm = Permission.objects.get(codename="view_invoice")
        self.user.user_permissions.add(perm)
        self.user.save()
        invoice = InvoiceFactory()
        resp = self.client.get(reverse("invoice_get", args=(invoice.id,)))
        self.assertEqual(200, resp.status_code)

    def test_with_weird_characters_in_event_name(self):
        """Checks for invoices with special names.

        Some characters are considered special characters by Latex and need
        proper escaping. This test checks that those are handled correctly.
        """
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        last_week = today - datetime.timedelta(days=7)
        event = EventFactory(
            organizer=self.to,
            date=yesterday,
            category=Event.Category.REGIONAL,
            name="Dangerous event '#'",
        )

        for _ in range(10):
            ResultFactory(event=event)

        invoice = InvoiceFactory(
            start_date=last_week, end_date=today, event_organizer=self.to
        )

        self.login()
        resp = self.client.get(reverse("invoice_get", args=(invoice.id,)))
        self.assertEqual(200, resp.status_code)

    def test_weird_characters_in_organizer_name(self):
        self.to.name = "Dangerous char '#'"
        self.to.save()
        invoice = InvoiceFactory(event_organizer=self.to)
        self.login()
        resp = self.client.get(reverse("invoice_get", args=(invoice.id,)))
        self.assertEqual(200, resp.status_code)

    def test_freeze_invoice(self):
        """Checks if we can freeze an invoice, meaning render it once and
        attach it as PDF."""
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        invoice = InvoiceFactory(event_organizer=self.to)
        self.login()

        data = {"action": "freeze", "_selected_action": [invoice.id]}
        resp = self.client.post(
            reverse("admin:invoicing_invoice_changelist"), data, follow=True
        )
        self.assertEqual(200, resp.status_code)

        # Check that a file was attached to the invoice
        invoice.refresh_from_db()
        self.assertTrue(invoice.frozen_file, "Should have a saved file.")


class FrozenInvoiceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.to = EventOrganizerFactory(user=self.user)
        self.login()
        self.invoice = InvoiceFactory(
            event_organizer=self.to,
        )
        self.invoice.frozen_file.save("", ContentFile(b"foobar"))

    def login(self):
        self.client.login(**self.credentials)

    def test_serve_frozen_invoice(self):
        resp = self.client.get(
            reverse("invoice_get", args=(self.invoice.id,)), follow=True
        )
        self.assertEqual(200, resp.status_code)
        self.assertEqual("foobar", resp.content.decode())

    def test_unfreeze_invoices(self):
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()

        data = {"action": "unfreeze", "_selected_action": [self.invoice.id]}
        resp = self.client.post(
            reverse("admin:invoicing_invoice_changelist"), data, follow=True
        )
        self.assertEqual(200, resp.status_code)
        self.invoice.refresh_from_db()
        self.assertFalse(
            self.invoice.frozen_file, "The frozen file should have been removed"
        )
