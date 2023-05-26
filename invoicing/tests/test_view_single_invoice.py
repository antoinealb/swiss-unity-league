from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from championship.models import *
from invoicing.models import Invoice
from championship.factories import EventFactory, EventOrganizerFactory


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
