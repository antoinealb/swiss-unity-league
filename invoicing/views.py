from django.shortcuts import render
from django.views.generic import DetailView, ListView
from django_tex.shortcuts import render_to_pdf
from .models import Invoice, fee_for_event
from django.db.models import F, Q, Count
from django.conf import settings

INVOICE_TEMPLATE = "invoicing/invoice.tex"


def get_invoice_pdf_context(invoice: Invoice):
    """Returns the context dict needed for rendering the invoice."""
    context = {}
    events = invoice.events.annotate(
        top8_cnt=Count(
            "eventplayerresult",
            filter=Q(eventplayerresult__single_elimination_result__gt=0),
        ),
        event_size=Count("eventplayerresult"),
    ).order_by("date")[:]

    for e in events:
        e.fees = fee_for_event(e)

    context["logo_path"] = str(settings.BASE_DIR / "static/sul_logo.png")
    context["start_date"] = invoice.start_date.strftime("%Y-%m-%d")
    context["end_date"] = invoice.end_date.strftime("%Y-%m-%d")
    context["events"] = events
    context["invoice"] = invoice

    return context


class RenderInvoice(DetailView):
    model = Invoice
    template_name = INVOICE_TEMPLATE
    object_name = "invoice"

    def get_context_data(self, **kwargs):
        context = get_invoice_pdf_context(self.object)
        context.update(kwargs)
        return super().get_context_data(**context)

    def render_to_response(self, context):
        template = self.get_template_names()[0]
        return render_to_pdf(self.request, template, context, filename=f"invoice.pdf")


class InvoiceList(ListView):
    model = Invoice

    def get_queryset(self):
        return Invoice.objects.filter(event_organizer__user=self.request.user)
