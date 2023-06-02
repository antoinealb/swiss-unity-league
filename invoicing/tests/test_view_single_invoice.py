import unittest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from championship.models import *
from invoicing.models import Invoice
from invoicing.factories import *
from championship.factories import EventFactory, EventOrganizerFactory
from subprocess import check_call, SubprocessError, DEVNULL


def has_latex():
    try:
        check_call(["lualatex", "--help"], stdout=DEVNULL, stderr=DEVNULL)
    except FileNotFoundError:
        return False
    return True


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
        invoice = Invoice.objects.create(
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
