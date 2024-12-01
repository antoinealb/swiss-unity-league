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

import datetime
import random

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Max
from django.views.generic.base import TemplateView

from articles.models import Article
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
        context["has_pending_registration"] = self._has_pending_registration()
        context["most_recent_article"] = self._most_recent_article()
        return context

    def _future_events(self):
        future_premier = (
            Event.objects.future_events()
            .filter(
                date__lte=datetime.date.today() + datetime.timedelta(days=30),
                category=Event.Category.PREMIER,
            )
            .order_by("date")[:PREMIERS_ON_PAGE]
            .prefetch_related("address", "organizer")
        )

        remaining_regionals = EVENTS_ON_PAGE - len(future_premier)
        future_regional = (
            Event.objects.future_events()
            .filter(category=Event.Category.REGIONAL)
            .order_by("date")[:remaining_regionals]
            .prefetch_related("address", "organizer")
        )
        # We sort by category as well, so that premier events on the same date
        # as a regional are shown first.
        future_events = list(future_regional) + list(future_premier)
        future_events.sort(key=lambda e: (e.date, e.category))
        return future_events

    def _most_recent_article(self):
        return Article.objects.published().order_by("-published_date").first()

    def _organizers_with_image(self):
        # Just make sure we don't always have the pictures in the same order
        # to be fair to everyone
        organizers = list(
            EventOrganizer.objects.exclude(image="")
            .exclude(image=None)
            .annotate(latest_event_date=Max("event__date"))
            .filter(
                latest_event_date__gt=datetime.date.today()
                - datetime.timedelta(days=365)
            )
        )
        random.shuffle(organizers)
        return organizers

    def _has_open_invoices(self) -> bool:
        if self.request.user.is_anonymous:
            return False

        return Invoice.objects.filter(
            event_organizer__user=self.request.user, payment_received_date__isnull=True
        ).exists()

    def _has_pending_registration(self):
        authorized = self.request.user.has_perm("auth.change_user")
        pending_registration = User.objects.filter(
            is_active=False, last_login__isnull=True
        )
        return authorized and pending_registration.exists()
