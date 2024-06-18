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
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.edit import CreateView

from dateutil.rrule import FR, MO, MONTHLY, SA, SU, TH, TU, WE, WEEKLY, rrule, rruleset

from championship.forms import RecurrenceRuleModelFormSet, RecurringEventForm
from championship.models import Event, RecurrenceRule, RecurringEvent

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


@transaction.atomic
def reschedule(recurring_event: RecurringEvent):
    """
    Reschedules all events linked to the given RecurringEvent, based on it's RecurrenceRules.
    Events with results are not rescheduled.
    Events rescheduled in the same week keep their primary key (and thus also their URL).
    """

    events_to_reschedule: list[Event] = list(
        recurring_event.event_set.annotate(
            result_cnt=Count("eventplayerresult")
        ).filter(result_cnt=0)
    )

    if events_to_reschedule:
        default_event = copy.deepcopy(events_to_reschedule[0])
    else:
        default_event = recurring_event.event_set.first()

    if not default_event:
        raise ValueError(
            "Rescheduling a recurring event requires at least one event linked to it."
        )

    all_dates, regional_dates = calculate_recurrence_dates(recurring_event)

    def find_event_for_same_week(events, given_date) -> Event | None:
        # Compares year and week number
        given_week = given_date.isocalendar()[:2]

        for index, event in enumerate(events):
            week_of_event = event.date.isocalendar()[:2]
            if week_of_event == given_week:
                return events.pop(index)
        return None

    for date in all_dates:
        # Try to find an event for the same week, else create a copy
        event = find_event_for_same_week(events_to_reschedule, date)
        if not event:
            event = default_event
            event.pk = None

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


class RecurringEventFromMixin:
    """Used to handle the rendering and saving of the combined forms for RecurringEvent and RecurrenceRule."""

    def render_forms(self, recurring_event_form, recurrence_rule_formset):
        return render(
            self.request,
            self.template_name,
            {
                "recurring_event_form": recurring_event_form,
                "recurrence_rule_formset": recurrence_rule_formset,
            },
        )

    def save_forms(self, recurring_event_form, recurrence_rule_formset):
        recurring_event = recurring_event_form.save()
        recurring_event.recurrencerule_set.all().delete()
        for form in recurrence_rule_formset:
            rule = form.save(commit=False)
            rule.recurring_event = recurring_event
            rule.save()
        return recurring_event


class RecurringEventCreateView(LoginRequiredMixin, RecurringEventFromMixin, View):
    """We implement a custom create view here, because we need to handle 2 forms and models at the same time."""

    template_name = "championship/recurring_event.html"
    success_url = reverse_lazy("events")

    def get(self, request, *args, **kwargs):
        return self.render_forms(RecurringEventForm(), RecurrenceRuleModelFormSet())

    def post(self, request, *args, **kwargs):
        recurring_event_form = RecurringEventForm(request.POST)
        recurrence_rule_formset = RecurrenceRuleModelFormSet(request.POST)
        if recurring_event_form.is_valid() and recurrence_rule_formset.is_valid():
            self.save_forms(recurring_event_form, recurrence_rule_formset)
            messages.success(request, "Recurring event successfully created.")
            return redirect(self.success_url)
        return self.render_forms(recurring_event_form, recurrence_rule_formset)


class RecurringEventUpdateView(LoginRequiredMixin, RecurringEventFromMixin, View):
    """We implement a custom update view here, because we need to handle 2 forms and models at the same time."""

    template_name = "championship/recurring_event.html"
    success_url = reverse_lazy("events")

    def get(self, request, *args, **kwargs):
        recurring_event = RecurringEvent.objects.get(pk=kwargs["pk"])
        recurring_event_form = RecurringEventForm(instance=recurring_event)
        recurrence_rule_formset = RecurrenceRuleModelFormSet(
            queryset=recurring_event.recurrencerule_set.all()
        )
        return self.render_forms(recurring_event_form, recurrence_rule_formset)

    def post(self, request, *args, **kwargs):
        recurring_event = RecurringEvent.objects.get(pk=kwargs["pk"])
        recurring_event_form = RecurringEventForm(
            request.POST, instance=recurring_event
        )
        recurrence_rule_formset = RecurrenceRuleModelFormSet(request.POST)
        if recurring_event_form.is_valid() and recurrence_rule_formset.is_valid():
            self.save_forms(recurring_event_form, recurrence_rule_formset)
            messages.success(request, "Recurring event successfully rescheduled.")
            return redirect(self.success_url)
        return self.render_forms(recurring_event_form, recurrence_rule_formset)
