from django.shortcuts import render
from django.views.generic import DetailView
from django_tex.shortcuts import render_to_pdf
from .models import Invoice
from django.db.models import F, Q, Count
from championship.billing import fee_for_event


class RenderInvoice(DetailView):
    model = Invoice
    template_name = "invoicing/invoice.tex"
    object_name = "invoice"

    def get_context_data(self, **kwargs):
        context = dict()
        events = self.object.events.annotate(
            top8_cnt=Count(
                "eventplayerresult",
                filter=Q(eventplayerresult__single_elimination_result__gt=0),
            ),
            event_size=Count("eventplayerresult"),
        ).order_by("date")[:]

        for e in events:
            e.fees = fee_for_event(e)

        context["start_date"] = self.object.start_date.strftime("%Y-%m-%d")
        context["end_date"] = self.object.end_date.strftime("%Y-%m-%d")
        context["events"] = events
        context["total_fees"] = sum(e.fees for e in events)

        context.update(kwargs)
        return super().get_context_data(**context)

    def render_to_response(self, context):
        template = self.get_template_names()[0]
        return render_to_pdf(self.request, template, context, filename=f"invoice.pdf")
