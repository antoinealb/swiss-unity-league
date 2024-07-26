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

import os.path
import tempfile
import zipfile
from typing import Iterable

from django.contrib import admin
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpResponse

from django_tex.core import compile_template_to_pdf

from invoicing.models import Invoice, PayeeAddress
from invoicing.views import INVOICE_TEMPLATE, get_invoice_pdf_context


class InvoiceAdmin(admin.ModelAdmin):
    search_fields = ["event_organizer__name"]
    list_filter = [
        "event_organizer",
        "sent_date",
        "payment_received_date",
    ]
    date_hierarchy = "end_date"
    list_display = (
        "event_organizer_name",
        "reference",
        "amount",
        "start_date",
        "end_date",
        "sent_date",
        "payment_received_date",
    )
    list_select_related = ["event_organizer"]

    exclude = ["frozen_file"]
    actions = ["download", "freeze", "unfreeze"]

    @admin.display(ordering="id", description="Reference number")
    def reference(self, instance: Invoice) -> str:
        return instance.reference

    @admin.display(ordering="event_organizer__name", description="Organizer name")
    def event_organizer_name(self, instance: Invoice):
        return instance.event_organizer.name

    @admin.display(description="Amount")
    def amount(self, instance: Invoice) -> str:
        return f"{instance.total_amount} CHF"

    @admin.action(description="Download selected invoices as PDF", permissions=["view"])
    def download(self, request, queryset: Iterable[Invoice]):
        with tempfile.TemporaryDirectory() as dir:
            zipname = os.path.join(dir, "out.zip")
            with zipfile.ZipFile(zipname, "w") as zipout:
                for invoice in queryset:
                    if invoice.frozen_file:
                        pdf_data = invoice.frozen_file.read()
                    else:
                        pdf_data = compile_template_to_pdf(
                            INVOICE_TEMPLATE, get_invoice_pdf_context(invoice)
                        )
                    pdfpath = os.path.join(
                        dir, f"{invoice.reference} - {invoice.event_organizer.name}.pdf"
                    )

                    with open(pdfpath, "wb") as f:
                        f.write(pdf_data)
                    arcname = os.path.join("invoices", os.path.basename(pdfpath))
                    zipout.write(pdfpath, arcname=arcname)

            with open(zipname, "rb") as f:
                response = HttpResponse(f, content_type="application/force-download")
                response["Content-Disposition"] = (
                    'attachment; filename="%s"' % "invoices.zip"
                )
                return response

    @admin.action(
        description="Freeze invoices PDF.",
        permissions=["change"],
    )
    @transaction.atomic
    def freeze(self, request, queryset: Iterable[Invoice]):
        for invoice in queryset:
            output = compile_template_to_pdf(
                INVOICE_TEMPLATE, get_invoice_pdf_context(invoice)
            )
            invoice.frozen_file.save("", ContentFile(output))
            invoice.save()

    @admin.action(
        description="Unfreeze invoices PDF.",
        permissions=["change"],
    )
    @transaction.atomic
    def unfreeze(self, request, queryset: Iterable[Invoice]):
        for invoice in queryset:
            invoice.frozen_file.delete()
            invoice.save()


admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(PayeeAddress)
