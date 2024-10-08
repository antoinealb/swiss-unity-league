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

from championship.factories import (
    Event2024Factory,
    EventFactory,
    EventOrganizerFactory,
    ResultFactory,
)
from championship.models import Event, EventOrganizer
from invoicing.factories import InvoiceFactory
from invoicing.models import Invoice


class InvoiceHelpersTest(TestCase):
    def test_str(self):
        o = EventOrganizer(name="Test TO")
        s = datetime.date(2023, 1, 1)
        e = datetime.date(2023, 1, 31)
        i = Invoice(event_organizer=o, start_date=s, end_date=e)

        self.assertEqual(str(i), "Test TO (01.01.2023 - 31.01.2023)")

    def test_reference_not_yet_saved(self):
        """For invoices that are not yet in the database, they don't have a
        reference number."""
        o = EventOrganizerFactory()
        s = datetime.date(2023, 1, 1)
        e = datetime.date(2023, 1, 31)
        i = Invoice(event_organizer=o, start_date=s, end_date=e)

        self.assertEqual(i.reference, "SUL###-####")

    def test_reference_saved(self):
        i = InvoiceFactory()
        self.assertEqual(i.reference, "SUL001-583")

    def test_discount_is_applied(self):
        o = EventOrganizerFactory()
        e = EventFactory(organizer=o, category=Event.Category.REGIONAL)
        # No top8, 10 players = 20 CHF
        for _ in range(10):
            ResultFactory(event=e)

        i = InvoiceFactory(
            event_organizer=o,
            start_date=e.date,
            end_date=datetime.date.today(),
            discount=19,
        )

        self.assertEqual(1, i.total_amount, "Discount should be applied")


class FindEventsTest(TestCase):
    def test_find_events_for_invoice(self):
        o = EventOrganizerFactory(name="Test TO")
        s = datetime.date(2023, 1, 1)
        e = datetime.date(2023, 1, 31)
        invoice = Invoice(event_organizer=o, start_date=s, end_date=e)

        want_events = [
            EventFactory(
                organizer=o,
                date=datetime.date(2023, 1, day),
                category=Event.Category.REGIONAL,
            )
            for day in (4, 5, 6)
        ]

        # This event is after the end of the invoice
        EventFactory(
            organizer=o,
            date=datetime.date(2023, 3, 1),
            category=Event.Category.REGIONAL,
        )

        # This event is a Regular, should not be on invoice
        EventFactory(
            organizer=o, date=datetime.date(2023, 1, 5), category=Event.Category.REGULAR
        )

        self.assertEqual(list(invoice.events), want_events)

    def test_events_for_invoice_can_be_marked_as_non_billed(self):
        """
        Some events can be excluded from invoices by admin (e.g. the invitational).

        This test checks that they are not included in invoices.
        """
        event = Event2024Factory(
            category=Event.Category.REGIONAL,
            include_in_invoices=False,
        )

        for _ in range(10):
            ResultFactory(event=event)

        invoice = InvoiceFactory(
            event_organizer=event.organizer,
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2024, 12, 31),
        )

        self.assertEqual(0, invoice.total_amount)
