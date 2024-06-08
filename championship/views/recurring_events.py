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

from django.db import transaction

from dateutil.rrule import FR, MO, MONTHLY, SA, SU, TH, TU, WE, WEEKLY, rrule, rruleset

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
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    # Make sure only future dates are considered
    start_date = max(recurring_event.start_date, tomorrow)
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
    Reschedules all future events of the given RecurringEvent, based on it's RecurrenceRules.
    Today's and past events stay the same.
    """
    events_to_reschedule = list(
        recurring_event.event_set.filter(date__gt=datetime.date.today())
    )

    if events_to_reschedule:
        default_event = events_to_reschedule[0]
    else:
        default_event = recurring_event.event_set.first()

    if not default_event:
        raise ValueError(
            "Rescheduling a recurring event requires at least one event linked to it."
        )

    regional_rule_exists = any(
        rule.type == RecurrenceRule.Type.REGIONAL
        for rule in recurring_event.recurrencerule_set.all()
    )

    all_dates, regional_dates = calculate_recurrence_dates(recurring_event)
    for date in all_dates:
        # If possible reschedule an upcoming event, otherwise make a copy of the default_event
        if events_to_reschedule:
            event = events_to_reschedule.pop(0)
        else:
            event = default_event
            event.pk = None

        event.date = date

        # If a regional rule exists, we need to set the category accordingly
        if regional_rule_exists:
            if date in regional_dates:
                event.category = Event.Category.REGIONAL
            else:
                event.category = Event.Category.REGULAR

        event.save()

    # Delete any events that could not be rescheduled due to fewer scheduled events
    for event in events_to_reschedule:
        event.delete()
