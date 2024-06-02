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
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView, UpdateView

from championship.forms import EventCreateForm
from championship.models import Event, EventPlayerResult, RecurrenceRule, RecurringEvent
from championship.score import get_results_with_qps
from championship.season import SEASON_LIST
from championship.views.base import CustomDeleteView


class EventDetailsView(DetailView):
    template_name = "championship/event_details.html"
    model = Event
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = context["event"]
        results = get_results_with_qps(
            EventPlayerResult.objects.filter(event=event).select_related("player")
        )

        context["can_edit_results"] = (
            event.can_be_edited() and event.organizer.user == self.request.user
        ) or self.request.user.is_superuser

        context["results"] = sorted(results)
        context["has_decklists"] = any(
            result.decklist_url for result, _ in context["results"]
        )

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

        messages.success(self.request, "Succesfully created event!")

        return HttpResponseRedirect(reverse("event_details", args=[event.id]))


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
        event.pk = None  # Force Django to create a new instance
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


def dates_from_recurrence_rules(
    recurrence_rules: list[RecurrenceRule], end_date: datetime.date
):
    """Returns a list of dates from the given recurrence rules.
    Starts from today and ends at the given end_date."""
    # TODO implement
    raise NotImplementedError()


# We can just allow the user to edit one of the RecurringEvent's events.
# When the user saves, then edit the data of the other events.
@transaction.atomic
def edit_recurring_event_data(recurring_event: RecurringEvent, new_event: Event):
    """Edits the data of all events of the given recurring event.
    @param new_event: An event containing the new data."""
    for event in recurring_event.event_set.all():
        new_event.pk = event.pk
        new_event.save()


# Called when the user saves the recurring event form
@transaction.atomic
def reschedule_recurring_event(recurring_event: RecurringEvent):
    """Reschedules all future events of the given recurring event.
    Past events keep their date."""
    events = recurring_event.event_set.all()

    if not events:
        # TODO Should not happen, if we build the UI correctly
        raise ValueError("No events found for recurring event")
    # Make sure we have a default event
    event = events[0]

    future_events_queue = [e for e in events if e.date > datetime.date.today()]
    for date in dates_from_recurrence_rules(
        recurring_event.recurrence_rule_set.all(), recurring_event.end_date
    ):
        # If possible edit the date of an upcoming event
        if future_events_queue:
            event = future_events_queue.pop(0)

        # Otherwise create a new one
        if not future_events_queue:
            event.pk = None

        event.date = date
        event.save()
    # Delete all remaining events, in case there are now less events than before
    for event in future_events_queue:
        event.delete()
