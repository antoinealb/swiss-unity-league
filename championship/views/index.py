import datetime
import random

from django.conf import settings
from django.views.generic.base import TemplateView

from championship.models import Event, EventOrganizer
from championship.score import get_leaderboard
from invoicing.models import Invoice

EVENTS_ON_PAGE = 5
PREMIERS_ON_PAGE = 3
PLAYERS_TOP = 10


class IndexView(TemplateView):
    template_name = "championship/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = get_leaderboard(settings.DEFAULT_SEASON)[:PLAYERS_TOP]
        context["future_events"] = self._future_events()
        context["organizers"] = self._organizers_with_image()
        context["has_open_invoices"] = self._has_open_invoices()
        return context

    def _future_events(self):
        future_premier = (
            Event.objects.filter(
                date__gte=datetime.date.today(),
                date__lte=datetime.date.today() + datetime.timedelta(days=30),
                category=Event.Category.PREMIER,
            )
            .order_by("date")[:PREMIERS_ON_PAGE]
            .prefetch_related("address", "organizer")
        )

        remaining_regionals = EVENTS_ON_PAGE - len(future_premier)
        future_regional = (
            Event.objects.filter(
                date__gte=datetime.date.today(), category=Event.Category.REGIONAL
            )
            .order_by("date")[:remaining_regionals]
            .prefetch_related("address", "organizer")
        )

        future_events = list(future_regional) + list(future_premier)
        future_events.sort(key=lambda e: e.date)
        return future_events

    def _organizers_with_image(self):
        # Just make sure we don't always have the pictures in the same order
        # to be fair to everyone
        organizers = list(EventOrganizer.objects.exclude(image="").exclude(image=None))
        random.shuffle(organizers)
        return organizers

    def _has_open_invoices(self) -> bool:
        if self.request.user.is_anonymous:
            return False

        return Invoice.objects.filter(
            event_organizer__user=self.request.user, payment_received_date__isnull=True
        ).exists()


class RobotsTxtView(TemplateView):
    template_name = "robots.txt"
    content_type = "text/plain"
