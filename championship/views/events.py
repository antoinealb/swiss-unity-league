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
from itertools import repeat
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView, UpdateView
from rest_framework import viewsets

from championship.forms import EventCreateForm
from championship.models import Event
from championship.score import get_results_with_qps
from championship.season import SEASON_LIST, find_season_by_slug
from championship.serializers import EventSerializer
from championship.views.base import CustomDeleteView
from decklists.models import Collection, Decklist


class EventDetailsView(DetailView):
    template_name = "championship/event_details.html"
    model = Event
    context_object_name = "event"

    def get_results(self, event):
        qs = event.result_set.all().select_related("player")

        # SUL Other events can have results in some cases (SUL invitational
        # only) but they don't give points, and get_results_with_qps will filter
        # them out. Just use None as scores.
        if event.category == Event.Category.OTHER:
            return zip(qs, repeat(None))
        return get_results_with_qps(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = context["event"]

        results = list(self.get_results(event))

        context["can_edit_results"] = (
            event.can_be_edited() and event.organizer.user == self.request.user
        ) or self.request.user.is_superuser

        context["results"] = sorted(results)
        context["has_league_points"] = any(points for _, points in results)

        context["collections"] = Collection.objects.filter(event=event).all()
        self.attach_decklists_to_results(results, context)
        context["any_decklist_submission_open"] = any(
            c for c in context["collections"] if not c.is_past_deadline
        )

        # We allow 1 collection only, unless event is multiformat.
        context["show_create_collection_link"] = (
            not context["collections"]
        ) or event.format == Event.Format.MULTIFORMAT

        # Prompt the players to notify the organizer that they forgot to upload results
        # Only do so when the event is finished longer than 4 days ago and results can still be uploaded.
        context["notify_missing_results"] = (
            event.date < timezone.now().date() - timezone.timedelta(days=4)
            and event.can_be_edited()
            and event.category != Event.Category.OTHER
        )

        return context

    def attach_decklists_to_results(self, results, context):
        """For each player find their most recent decklist in the collection and attach it to their result.
        If the player doesn't have a result, we show the decklist in the unmatched decklists section.
        """
        event = context["event"]
        context["unmatched_decklists"] = []
        for collection in (
            context["collections"]
            .published()
            .filter(event=event)
            .prefetch_related(
                Prefetch(
                    "decklist_set",
                    queryset=Decklist.objects.select_related("player").order_by(
                        "-last_modified"
                    ),
                )
            )
        ):
            for decklist in collection.decklist_set.all():
                result = next(
                    (
                        result
                        for result, _ in results
                        if result.player_id == decklist.player_id
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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if Event.Category.requires_permission(form.instance.category):
            form.instance.category = Event.Category.OTHER
        return form

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
        future_events = {"Upcoming": ""}
        past_events_each_season = [
            {s.name: reverse("past-events-list", kwargs={"slug": s.slug})}
            for s in SEASON_LIST
        ]
        context["season_urls"] = [future_events] + past_events_each_season

        future_events = (
            Event.objects.future_events()
            .select_related("organizer", "address", "organizer__default_address")
            .order_by("date")
        )

        events = EventSerializer(
            future_events, many=True, context={"request": self.request}
        )
        context["events"] = events.data

        return context


class PastEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for the upcoming events page, showing past events."""

    serializer_class = EventSerializer

    def get_queryset(self):
        """Returns all Events in the past."""

        self.slug = self.kwargs.get("slug")
        try:
            season = find_season_by_slug(self.slug)
        except KeyError:
            raise Http404(f"Unknown season {self.slug}")

        return (
            Event.objects.in_season(season)
            .past_events()
            .select_related("organizer", "address", "organizer__default_address")
            .order_by("-date")
        )
