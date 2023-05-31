from django.contrib import admin
from django.http import HttpResponse
from django_tex.core import compile_template_to_pdf
from invoicing.models import Invoice
from invoicing.views import get_invoice_pdf_context, INVOICE_TEMPLATE
from typing import Iterable
import tempfile
import os.path
import zipfile


class InvoiceAdmin(admin.ModelAdmin):
    search_fields = ["event_organizer__name"]
    list_filter = ["event_organizer"]
    date_hierarchy = "end_date"
    list_display = (
        "event_organizer_name",
        "reference",
        "amount",
        "start_date",
        "end_date",
        "payment_received_date",
    )
    actions = ["download"]

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


admin.site.register(Invoice, InvoiceAdmin)
