import unittest
import os
from django.test import TestCase, Client, tag
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from parameterized import parameterized
from championship.models import *
from invoicing.models import Invoice
from invoicing.factories import *
from championship.factories import (
    EventFactory,
    EventOrganizerFactory,
    EventPlayerResultFactory,
)
from subprocess import check_call, DEVNULL


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
            name=f"Dangerous event '#'",
        )

        for _ in range(10):
            EventPlayerResultFactory(event=event)

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
