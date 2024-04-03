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

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import DetailView, ListView

from django_tex.shortcuts import render_to_pdf

from .models import Invoice, fee_for_event

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


class RenderInvoice(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = INVOICE_TEMPLATE
    object_name = "invoice"

    def dispatch(self, request, *args, **kwargs):
        own_invoice = self.get_object().event_organizer.user == request.user
        is_viewer = self.request.user.has_perm("invoicing.view_invoice")
        allowed = own_invoice or is_viewer

        if not allowed:
            raise Http404

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = get_invoice_pdf_context(self.object)
        context.update(kwargs)
        return super().get_context_data(**context)

    def render_to_response(self, context):
        invoice = self.get_object()
        if invoice.frozen_file:
            return redirect(invoice.frozen_file.url)

        template = self.get_template_names()[0]
        return render_to_pdf(self.request, template, context, filename="invoice.pdf")


class InvoiceList(LoginRequiredMixin, ListView):
    model = Invoice

    def get_queryset(self):
        return Invoice.objects.filter(event_organizer__user=self.request.user)
