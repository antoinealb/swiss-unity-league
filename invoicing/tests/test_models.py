import datetime
from django.test import TestCase
from invoicing.models import Invoice
from championship.models import EventOrganizer
from championship.factories import *


class InvoiceHelpersTest(TestCase):
    def test_str(self):
        o = EventOrganizer(name="Test TO")
        s = datetime.date(2023, 1, 1)
        e = datetime.date(2023, 1, 31)
        i = Invoice(event_organizer=o, start_date=s, end_date=e)

        self.assertEqual(str(i), "Test TO (01.01.2023 - 31.01.2023)")


class FindEventsTest(TestCase):
    def test_find_events_for_invoice(self):
        o = EventOrganizerFactory(name="Test TO")
        s = datetime.date(2023, 1, 1)
        e = datetime.date(2023, 1, 31)
        invoice = Invoice(event_organizer=o, start_date=s, end_date=e)

        want_events = [
            EventFactory(organizer=o, date=datetime.date(2023, 1, day))
            for day in (4, 5, 6)
        ]

        # This event is after the end of the invoice
        EventFactory(organizer=o, date=datetime.date(2023, 3, 1))

        # This event is not organized by the same to
        EventFactory()

        self.assertEqual(list(invoice.events), want_events)
