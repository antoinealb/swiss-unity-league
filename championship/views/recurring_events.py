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

from dateutil.rrule import FR, MO, MONTHLY, SA, SU, TH, TU, WE, WEEKLY, rruleset

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


def calculate_recurrence_dates(recurring_event: RecurringEvent):
    """Returns a list of dates from the given recurrence rules.
    Starts from today and ends at the given end_date."""

    start_date = recurring_event.start_date
    end_date = recurring_event.end_date

    # Somehow I need to import it here, so that it's available for the function
    from dateutil.rrule import rrule

    def get_rrule(rule: RecurrenceRule):
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

    rset = rruleset()
    regional_rset = rruleset()

    for rule in recurring_event.recurrencerule_set.all():

        if rule.type == RecurrenceRule.Type.SCHEDULE:
            rset.rrule(get_rrule(rule))
        elif rule.type == RecurrenceRule.Type.SKIP:
            rset.exrule(get_rrule(rule))
        elif rule.type == RecurrenceRule.Type.REGIONAL:
            rrule = get_rrule(rule)
            regional_rset.rrule(rrule)
            rset.exrule(rrule)

    return list(rset), list(regional_rset)
