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

import base64
import datetime
import io
from collections.abc import Iterator

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect
from django.template.defaultfilters import date
from django.views.generic import DetailView, ListView, TemplateView

import matplotlib

from championship.seasons.helpers import get_main_seasons

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from django_tex.shortcuts import render_to_pdf
from matplotlib.ticker import FormatStrFormatter

from championship.models import Event
from championship.seasons.definitions import Season

from .models import DiscountType, Invoice, fee_for_event

INVOICE_TEMPLATE = "invoicing/invoice.tex"


def get_invoice_pdf_context(invoice: Invoice):
    """Returns the context dict needed for rendering the invoice."""
    context = {}
    events = invoice.events.annotate(
        top8_cnt=Count(
            "result",
            filter=Q(result__playoff_result__gt=0),
        ),
        event_size=Count("result"),
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


class Report(PermissionRequiredMixin, TemplateView):
    template_name = "invoicing/report.html"
    permission_required = "invoicing.view_invoice"

    def data_points_for_season(self, season: Season) -> Iterator[tuple[int, int]]:
        events = (
            Event.objects.filter(
                category__in=[Event.Category.PREMIER, Event.Category.REGIONAL],
                date__gte=season.start_date,
                date__lte=season.end_date,
            )
            .annotate(result_cnt=Count("result"))
            .exclude(result_cnt=0)
            .order_by("date")
            .prefetch_related("result_set")
        )

        discounts = dict(self.map_discounts_to_event(season))

        revenue = 0
        for event in events:
            days_since_start = (event.date - season.start_date).days
            revenue += fee_for_event(event)
            revenue -= discounts.get(event, 0)
            yield days_since_start, revenue

    def map_discounts_to_event(self, season: Season) -> Iterator[tuple[Event, int]]:
        invoices = Invoice.objects.filter(
            start_date__gte=season.start_date,
            end_date__lte=season.end_date,
            discount__gt=0,
        ).exclude(discount_type=DiscountType.PAYMENT)

        for invoice in invoices:
            # Take the invoice's first event, putting priority on Premier
            event = Event.objects.filter(
                organizer=invoice.event_organizer,
                date__gte=invoice.start_date,
                date__lte=invoice.end_date,
                category__in=(Event.Category.PREMIER, Event.Category.REGIONAL),
            ).earliest("category", "date")

            yield event, invoice.discount

    def plot_revenue(self) -> bytes:
        """Plots the revenue of the SUL over time

        Returns:
            The plot's content in PNG bytes.
        """
        plt.figure()
        legends = []
        for s in sorted(get_main_seasons(), key=lambda s: s.start_date):
            data = list(self.data_points_for_season(s))

            if not data:
                continue

            legends.append(s.name)
            x, y = list(zip(*data))
            plt.plot(x, y, "-")

        plt.gca().yaxis.set_major_formatter(FormatStrFormatter("%d CHF"))

        today = date(datetime.date.today())
        plt.title(f"Evolution of SUL revenue per season\n(as of {today})")
        plt.ylabel("Revenue")
        plt.xlabel("Days since season start")
        plt.legend(legends)
        plt.grid()

        plt.tight_layout()
        output = io.BytesIO()
        plt.savefig(output, format="png")
        return output.getvalue()

    def encode_image(self, image: bytes, format_mime: str = "image/png") -> str:
        encoded_image = base64.b64encode(image).decode()
        return f"data:{format_mime};charset=utf-8;base64,{encoded_image}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["revenue_plot"] = self.encode_image(self.plot_revenue())
        return context
