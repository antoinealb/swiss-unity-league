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
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView, UpdateView
from rest_framework import viewsets

from championship.forms import EventCreateForm
from championship.models import Event, Result
from championship.score import get_results_with_qps
from championship.season import SEASON_LIST, find_season_by_slug
from championship.serializers import EventSerializer
from championship.views.base import CustomDeleteView
from decklists.models import Collection, Decklist


class EventDetailsView(DetailView):
    template_name = "championship/event_details.html"
    model = Event
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = context["event"]
        results = list(
            get_results_with_qps(
                Result.objects.filter(event=event).select_related("player")
            )
        )

        context["can_edit_results"] = (
            event.can_be_edited() and event.organizer.user == self.request.user
        ) or self.request.user.is_superuser

        context["results"] = sorted(results)

        context["unmatched_decklists"] = []
        for collection in Collection.objects.filter(
            event=event,
            publication_time__lt=datetime.datetime.now(),
        ).prefetch_related(
            Prefetch(
                "decklist_set", queryset=Decklist.objects.order_by("-last_modified")
            )
        ):
            for decklist in collection.decklist_set.all():
                result = next(
                    (
                        result
                        for result, _ in results
                        if result.player == decklist.player
                    ),
                    None,
                )
                if result is None:
                    context["unmatched_decklists"].append(decklist)
                else:
                    context["has_decklists"] = True
                    if not hasattr(result, "decklists"):
                        result.decklists = []
                    if not any([d.collection == collection for d in result.decklists]):
                        result.decklists.append(decklist)

        # Prompt the players to notify the organizer that they forgot to upload results
        # Only do so when the event is finished longer than 4 days ago and results can still be uploaded.
        context["notify_missing_results"] = (
            event.date < datetime.date.today() - datetime.timedelta(days=4)
            and event.can_be_edited()
            and event.category != Event.Category.OTHER
        )
        return context


class CreateEventView(LoginRequiredMixin, FormView):
    template_name = "championship/create_event.html"
    form_class = EventCreateForm

    def get_form_kwargs(self):
        kwargs = super(CreateEventView, self).get_form_kwargs()
        kwargs["organizer"] = self.request.user.eventorganizer

        default_address = kwargs["organizer"].default_address
        if default_address:
            kwargs["initial"]["address"] = default_address.id
        return kwargs

    def form_valid(self, form):
        event = form.save(commit=False)
        event.organizer = self.request.user.eventorganizer
        event.save()

        messages.success(self.request, "Successfully created event!")
        if self.request.POST.get("submit_type") == "schedule_series":
            redirect_view_name = "recurring_event_create"
        else:
            redirect_view_name = "event_details"
        return HttpResponseRedirect(reverse(redirect_view_name, args=[event.id]))


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventCreateForm
    template_name = "championship/update_event.html"

    def dispatch(self, request, *args, **kwargs):
        self.event = self.get_object()
        if self.event.organizer.user != request.user or not self.event.can_be_edited():
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Check again if the event can be edited, because date could have changed."""
        event = form.save(commit=False)
        if not event.can_be_edited():
            messages.error(self.request, "Event date is too old.")
            return self.form_invalid(form)
        event.save()
        messages.success(self.request, "Successfully saved event")
        return HttpResponseRedirect(reverse("event_details", args=[self.object.id]))


class CopyEventView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventCreateForm
    template_name = "championship/copy_event.html"

    def get_initial(self):
        # By default, copy it one week later
        initial = super().get_initial()
        initial["date"] = self.object.date + datetime.timedelta(days=7)
        return initial

    def form_valid(self, form):
        event = form.save(commit=False)
        # Make sure the copy is deattached from the recurring event
        event = Event().copy_values_from(event, excluded_fields=["recurring_event"])
        event.organizer = self.request.user.eventorganizer
        event.save()
        messages.success(self.request, "Successfully created event!")
        return HttpResponseRedirect(reverse("event_details", args=[event.id]))


class EventDeleteView(CustomDeleteView):
    model = Event

    def get_success_url(self):
        return reverse("organizer_details", args=[self.object.organizer.id])

    def allowed_to_delete(self, event, request):
        return event.can_be_deleted() and event.organizer.user == request.user


class FutureEventView(TemplateView):
    template_name = "championship/future_events.html"

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        future_events = {"Upcoming": reverse("future-events-list")}
        past_events_each_season = [
            {s.name: reverse("past-events-list", kwargs={"slug": s.slug})}
            for s in SEASON_LIST
        ]
        context["season_urls"] = [future_events] + past_events_each_season
        return context


class FutureEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for the upcoming events page, showing future events."""

    serializer_class = EventSerializer

    def get_queryset(self):
        """Returns all Events in the future."""

        # This needs to be a function (get_queryset) instead of an attribute as
        # otherwise the today means "when the app was started.
        qs = Event.objects.filter(date__gte=datetime.date.today())
        qs = qs.select_related("organizer", "address", "organizer__default_address")
        return qs.order_by("date")


class PastEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for the upcoming events page, showing past events."""

    serializer_class = EventSerializer

    def get_queryset(self):
        """Returns all Events in the past."""

        self.slug = self.kwargs.get("slug")
        try:
            self.current_season = find_season_by_slug(self.slug)
        except KeyError:
            raise Http404(f"Unknown season {self.slug}")

        # This needs to be a function (get_queryset) instead of an attribute as
        # otherwise the today means "when the app was started.
        qs = Event.objects.filter(date__lt=datetime.date.today())
        qs = qs.filter(
            date__gte=self.current_season.start_date,
            date__lte=self.current_season.end_date,
        )
        qs = qs.select_related("organizer", "address", "organizer__default_address")
        return qs.order_by("-date")
