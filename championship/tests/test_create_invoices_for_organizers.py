import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from championship.factories import *
from championship.models import *
from invoicing.models import Invoice


class CreateInvoiceForOrganizerTestCase(TestCase):
    def setUp(self):
        User.objects.create_user(
            username="test", password="test", is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.login(username="test", password="test")
        self.organizers = [EventOrganizerFactory() for _ in range(3)]

    def create_invoices_for_organizers(self, organizers):
        data = {
            "action": "create_invoices",
            "_selected_action": [o.pk for o in organizers],
        }

        response = self.client.post(
            reverse("admin:championship_eventorganizer_changelist"), data, follow=True
        )

    def create_fake_event_with_results(
        self, organizer: EventOrganizer, date: datetime.date = datetime.date(2023, 1, 1)
    ) -> Event:
        event = EventFactory(
            organizer=organizer,
            category=Event.Category.REGIONAL,
            date=datetime.date(2023, 1, 1),
        )

        for _ in range(10):
            EventPlayerResultFactory(event=event)

    def test_can_create_invoice_for_organizers(self):
        """Checks that we can create invoices for an organizer from the admin page."""
        for o in self.organizers:
            self.create_fake_event_with_results(o)

        self.create_invoices_for_organizers(self.organizers)

        # We should have one invoice for each organizer
        for o in self.organizers:
            self.assertEqual(1, Invoice.objects.filter(event_organizer=o).count())

    def test_does_not_create_invoice_when_there_are_no_events(self):
        """No invoice is created when the organizer has no events."""

        # Only the first event organizer has results
        self.create_fake_event_with_results(self.organizers[0])

        # Yet we create invoices for everyone
        self.create_invoices_for_organizers(self.organizers)

        # Then we only have one invoice
        self.assertEqual(1, Invoice.objects.count())
