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

import copy
import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic.edit import UpdateView

from dateutil.rrule import FR, MO, MONTHLY, SA, SU, TH, TU, WE, WEEKLY, rrule, rruleset

from championship.forms import (
    EventCreateForm,
    RecurrenceRuleModelFormSet,
    RecurringEventForm,
    UpdateAllEventForm,
)
from championship.models import Event, RecurrenceRule, RecurringEvent
from championship.views.base import CustomDeleteView

WEEKDAY_MAP = {
    "MONDAY": MO,
    "TUESDAY": TU,
    "WEDNESDAY": WE,
    "THURSDAY": TH,
    "FRIDAY": FR,
    "SATURDAY": SA,
    "SUNDAY": SU,
}

WEEK_OF_MONTH_MAP = {
    "FIRST_WEEK": 1,
    "SECOND_WEEK": 2,
    "SECOND_LAST_WEEK": -2,
    "LAST_WEEK": -1,
}


def _get_rrule(rule: RecurrenceRule, recurring_event: RecurringEvent) -> rrule:
    start_date = recurring_event.start_date
    end_date = recurring_event.end_date
    weekday = WEEKDAY_MAP[rule.weekday]

    if rule.week == RecurrenceRule.Week.EVERY:
        return rrule(WEEKLY, byweekday=weekday, dtstart=start_date, until=end_date)
    elif rule.week == RecurrenceRule.Week.EVERY_OTHER:
        return rrule(
            WEEKLY,
            interval=2,
            byweekday=weekday,
            dtstart=start_date,
            until=end_date,
        )
    else:
        week_num = WEEK_OF_MONTH_MAP[rule.week]
        return rrule(
            MONTHLY,
            byweekday=weekday(week_num),
            dtstart=start_date,
            until=end_date,
        )


def calculate_recurrence_dates(
    recurring_event: RecurringEvent,
) -> tuple[list[datetime.date], list[datetime.date]]:
    """Returns two lists of dates as a tuple based on the given recurrence rules between
    the start_date and end_date of the recurring event.
    - The first list contains all scheduled dates.
    - The second list contains all dates, where the event is SUL Regional."""
    rset = rruleset()
    regional_rset = rruleset()

    for rule in recurring_event.recurrencerule_set.all():
        _rrule = _get_rrule(rule, recurring_event)
        if rule.type == RecurrenceRule.Type.SCHEDULE:
            rset.rrule(_rrule)
        elif rule.type == RecurrenceRule.Type.SKIP:
            rset.exrule(_rrule)
        elif rule.type == RecurrenceRule.Type.REGIONAL:
            regional_rset.rrule(_rrule)
            rset.exrule(_rrule)

    other_dates = [date.date() for date in rset]
    regional_dates = [date.date() for date in regional_rset]
    all_dates = sorted(set(other_dates + regional_dates))
    return all_dates, regional_dates


class NoLinkedEventError(ValueError):
    pass


class NoDatesError(ValueError):
    ui_message = "Between the start date and end date we cannot schedule any events based on the recurrence rules provided."

    def __init__(self):
        super().__init__(
            "'calculate_recurrence_dates' didn't find any dates based on the given recurrence rules between the start and end dates"
        )


@transaction.atomic
def reschedule(recurring_event: RecurringEvent):
    """
    Reschedules all events linked to the given RecurringEvent, based on it's RecurrenceRules.
    Events with results are not rescheduled.
    Events rescheduled in the same week keep their primary key (and thus also their URL).
    """

    events: list[Event] = list(
        recurring_event.event_set.annotate(result_cnt=Count("result")).all()
    )

    events_to_reschedule = [event for event in events if event.result_cnt == 0]
    dates_of_events_to_keep = [event.date for event in events if event.result_cnt > 0]

    if events_to_reschedule:
        default_event = events_to_reschedule[-1]
    else:
        default_event = recurring_event.get_most_recent_event()

    if not default_event:
        raise NoLinkedEventError(
            "Rescheduling a recurring event requires at least one event linked to it."
        )

    all_dates, regional_dates = calculate_recurrence_dates(recurring_event)

    if not all_dates:
        raise NoDatesError()

    def find_event_for_same_week(events, given_date) -> Event | None:
        # Compares year and week number
        given_week = given_date.isocalendar()[:2]

        for index, event in enumerate(events):
            week_of_event = event.date.isocalendar()[:2]
            if week_of_event == given_week:
                return events.pop(index)
        return None

    for date in all_dates:
        # If an event we keep (with results entered) is scheduled for this date, we skip it
        if date in dates_of_events_to_keep:
            continue
        # Try to find an event for the same week, else create a copy
        event = find_event_for_same_week(events_to_reschedule, date)
        if not event:
            event = Event().copy_values_from(default_event)

        event.date = date

        if regional_dates:
            if date in regional_dates:
                event.category = Event.Category.REGIONAL
            else:
                event.category = Event.Category.REGULAR

        event.save()

    # Delete any events that could not be rescheduled
    for event in events_to_reschedule:
        event.delete()


class RecurringEventFormMixin:
    """Used to handle the rendering and saving of the combined forms for RecurringEvent and RecurrenceRule."""

    template_name = "championship/recurring_event.html"

    def render_forms(self, recurring_event_form, recurrence_rule_formset):
        return render(
            self.request,
            self.template_name,
            {
                "recurring_event_form": recurring_event_form,
                "recurrence_rule_formset": recurrence_rule_formset,
                "leading_title": self.leading_title,
            },
        )

    def save_forms_if_valid(
        self, request, recurring_event_form, recurrence_rule_formset
    ):
        if recurring_event_form.is_valid() and recurrence_rule_formset.is_valid():
            # Save the recurring event and link the event to it.
            recurring_event = recurring_event_form.save()
            self.event.recurring_event = recurring_event
            self.event.save()

            # Delete all old rules and save the new ones
            recurring_event.recurrencerule_set.all().delete()
            for form in recurrence_rule_formset:
                rule = form.save(commit=False)
                rule.recurring_event = recurring_event
                rule.save()
            try:
                reschedule(recurring_event)
            except NoDatesError as e:
                # If there are no dates to schedule, we delete the recurring event and show an error message
                recurring_event.delete()
                messages.error(
                    request,
                    e.ui_message,
                )
                return self.render_forms(recurring_event_form, recurrence_rule_formset)
            messages.success(request, "Event series successfully scheduled.")
            return redirect(
                reverse(
                    "organizer_details",
                    args=[self.event.organizer.pk],
                )
            )
        return self.render_forms(recurring_event_form, recurrence_rule_formset)


class RecurringEventCreateView(LoginRequiredMixin, RecurringEventFormMixin, View):
    """We implement a custom create view here, because we need to handle 2 forms and models at the same time."""

    leading_title = "Create"

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, pk=kwargs["event_id"])
        # If the event is already part of a recurring event, we don't allow to create a new one
        if self.event.recurring_event_id:
            return HttpResponseForbidden()
        if self.event.organizer.user != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        formset = RecurrenceRuleModelFormSet()
        # set query set to none, otherwise the formset will be prefilled with all existing rules
        formset.queryset = RecurrenceRule.objects.none()
        return self.render_forms(RecurringEventForm(), formset)

    def post(self, request, *args, **kwargs):
        recurring_event_form = RecurringEventForm(request.POST)
        recurrence_rule_formset = RecurrenceRuleModelFormSet(request.POST)
        return self.save_forms_if_valid(
            request, recurring_event_form, recurrence_rule_formset
        )


class RecurringEventUpdateView(LoginRequiredMixin, RecurringEventFormMixin, View):
    """We implement a custom update view here, because we need to handle 2 forms and models at the same time."""

    leading_title = "Update Schedule of"

    def dispatch(self, request, *args, **kwargs):
        self.recurring_event = get_object_or_404(RecurringEvent, pk=kwargs["pk"])
        self.event = self.recurring_event.event_set.last()
        if self.event.organizer.user != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        recurring_event_form = RecurringEventForm(instance=self.recurring_event)
        recurrence_rule_formset = RecurrenceRuleModelFormSet(
            queryset=self.recurring_event.recurrencerule_set.all()
        )
        # We tell django there are no forms to update (no initial forms). This allows the user to define a new ruleset
        # by adding and removing rules. In the end, we will delete all old rules and save the new ones.
        recurrence_rule_formset.management_form.initial["INITIAL_FORMS"] = 0
        return self.render_forms(recurring_event_form, recurrence_rule_formset)

    def post(self, request, *args, **kwargs):
        recurring_event_form = RecurringEventForm(
            request.POST, instance=self.recurring_event
        )
        recurrence_rule_formset = RecurrenceRuleModelFormSet(request.POST)
        return self.save_forms_if_valid(
            request, recurring_event_form, recurrence_rule_formset
        )


class RecurringEventCopyView(RecurringEventUpdateView):
    """Copies a recurring event and reschedules the events."""

    leading_title = "Copy"

    def post(self, request, *args, **kwargs):
        # Create a copy of the last event
        self.event = self.recurring_event.event_set.last()
        self.event.pk = None
        # Copy the recurring event, by not passing a previous instance
        recurring_event_form = RecurringEventForm(request.POST)
        recurrence_rule_formset = RecurrenceRuleModelFormSet(request.POST)
        return self.save_forms_if_valid(
            request, recurring_event_form, recurrence_rule_formset
        )


class RecurringEventDeleteView(CustomDeleteView):
    model = RecurringEvent

    def get_success_url(self):
        return reverse("organizer_details", args=[self.event.organizer_id])

    def allowed_to_delete(self, recurring_event, request):
        self.event = recurring_event.event_set.last()
        return self.event.organizer.user == request.user

    def form_valid(self, form):
        # Delete all events linked to the recurring event without results
        self.object.event_set.annotate(result_cnt=Count("result")).filter(
            result_cnt=0
        ).delete()
        return super().form_valid(form)


class RecurringEventUpdateAllEventView(LoginRequiredMixin, UpdateView):
    """This view allows the user to edit all events linked to a recurring event at once."""

    model = Event
    form_class = UpdateAllEventForm
    template_name = "championship/update_event.html"

    def dispatch(self, request, *args, **kwargs):
        if not kwargs.get("pk"):
            event = get_object_or_404(
                RecurringEvent, pk=self.kwargs["recurring_event"]
            ).get_most_recent_event()
            return HttpResponseRedirect(reverse("event_update_all", args=[event.id]))
        self.event = self.get_object()
        if self.event.organizer.user != request.user or not self.event.recurring_event:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        update = form.save(commit=False)
        events = update.recurring_event.event_set.annotate(
            result_cnt=Count("result")
        ).filter(result_cnt=0)
        for event in events:
            event.copy_values_from(update, excluded_fields=["date", "category"]).save()
        messages.success(self.request, "Successfully updated all events")
        return HttpResponseRedirect(
            reverse("organizer_details", args=[self.object.organizer.id])
        )
