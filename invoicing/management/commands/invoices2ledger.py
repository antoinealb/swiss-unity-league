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
                Income:SUL Fees:{invoice.event_organizer.name}
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
                Income:SUL Fees:{invoice.event_organizer.name}
            """
                )
            )
