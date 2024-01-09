import datetime
import textwrap

from django.core.management.base import BaseCommand

from invoicing.models import Invoice


class Command(BaseCommand):
    help = "Convert all paid invoices into a format that can be understood by https://ledger-cli.org/."

    def handle(self, *args, **kwargs):
        for invoice in (
            Invoice.objects.exclude(payment_received_date__isnull=True)
            .select_related("event_organizer")
            .order_by("payment_received_date", "id")
        ):
            print(
                textwrap.dedent(
                    f"""\
            {invoice.payment_received_date.strftime('%Y-%m-%d')} {invoice.event_organizer.name} # { invoice.reference }
                Assets:Bank  CHF{invoice.total_amount}
                Income:SUL Fees
            """
                )
            )

        for invoice in (
            Invoice.objects.filter(payment_received_date__isnull=True)
            .select_related("event_organizer")
            .order_by("payment_received_date", "id")
        ):
            print(
                textwrap.dedent(
                    f"""\
            {invoice.created_date.strftime('%Y-%m-%d')} {invoice.event_organizer.name} # { invoice.reference }
                Assets:Account Receivable:SUL Fees  CHF{invoice.total_amount}
                Income:SUL Fees
            """
                )
            )
