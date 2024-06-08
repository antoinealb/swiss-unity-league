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

from django.forms import ValidationError
from django.test import TestCase

from freezegun import freeze_time

from championship.factories import (
    EventFactory,
    RecurrenceRuleFactory,
    RecurringEventFactory,
)
from championship.models import Event, RecurrenceRule
from championship.views.recurring_events import calculate_recurrence_dates, reschedule


class RecurringEventModelTest(TestCase):

    def test_end_date_deep_in_future_throw_validation_error(self):
        # We only allow recurring events to be scheduled for up to a year.
        event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=365),
        )
        event.full_clean()
        with self.assertRaises(ValidationError):
            event = RecurringEventFactory(
                end_date=datetime.date.today() + datetime.timedelta(days=366),
            )
            event.full_clean()


class RecurrenceScheduleTest(TestCase):

    @freeze_time("2024-06-01")
    def test_weekly_recurrence(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=15),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        dates, regional_dates = calculate_recurrence_dates(recurring_event)
        self.assertEqual(dates, [datetime.date(2024, 6, 7), datetime.date(2024, 6, 14)])
        self.assertEqual(regional_dates, [])

    @freeze_time("2024-06-01")
    def test_biweekly_recurrence(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.EVERY_OTHER,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        dates, _ = calculate_recurrence_dates(recurring_event)
        self.assertEqual(
            dates,
            [
                datetime.date(2024, 6, 14),
                datetime.date(2024, 6, 28),
                datetime.date(2024, 7, 12),
                datetime.date(2024, 7, 26),
            ],
        )

    @freeze_time("2024-06-01")
    def test_recurring_first_monday_and_last_friday_of_month(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.MONDAY,
            week=RecurrenceRule.Week.FIRST,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.LAST,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        dates, _ = calculate_recurrence_dates(recurring_event)
        self.assertEqual(
            dates,
            [
                datetime.date(2024, 6, 3),
                datetime.date(2024, 6, 28),
                datetime.date(2024, 7, 1),
                datetime.date(2024, 7, 26),
            ],
        )

    @freeze_time("2024-06-01")
    def test_every_friday_except_the_last_of_month(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.LAST,
            type=RecurrenceRule.Type.SKIP,
            recurring_event=recurring_event,
        )
        dates, _ = calculate_recurrence_dates(recurring_event)

        self.assertEqual(
            dates,
            [
                datetime.date(2024, 6, 7),
                datetime.date(2024, 6, 14),
                datetime.date(2024, 6, 21),
                datetime.date(2024, 7, 5),
                datetime.date(2024, 7, 12),
                datetime.date(2024, 7, 19),
            ],
        )

    @freeze_time("2024-06-01")
    def test_every_first_friday_regional(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.FIRST,
            type=RecurrenceRule.Type.REGIONAL,
            recurring_event=recurring_event,
        )
        other_dates, regional_dates = calculate_recurrence_dates(recurring_event)

        self.assertEqual(
            other_dates,
            [
                datetime.date(2024, 6, 14),
                datetime.date(2024, 6, 21),
                datetime.date(2024, 6, 28),
                datetime.date(2024, 7, 12),
                datetime.date(2024, 7, 19),
                datetime.date(2024, 7, 26),
            ],
        )

        self.assertEqual(
            regional_dates,
            [
                datetime.date(2024, 6, 7),
                datetime.date(2024, 7, 5),
            ],
        )

    @freeze_time("2024-06-01")
    def test_past_recurrence_dates_not_calculated(self):
        recurring_event = RecurringEventFactory(
            start_date=datetime.date.today() - datetime.timedelta(days=15),
            end_date=datetime.date.today() + datetime.timedelta(days=7),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        dates, regional_dates = calculate_recurrence_dates(recurring_event)
        self.assertEqual(
            dates,
            [
                datetime.date(2024, 6, 7),
            ],
        )
        self.assertEqual(regional_dates, [])


class RecurrenceEventCreationTest(TestCase):

    @freeze_time("2024-06-01")
    def test_create_series_from_event_today(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=30),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.WEDNESDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        initial_event = EventFactory(
            recurring_event=recurring_event,
            date=datetime.date.today(),
        )
        reschedule(recurring_event)
        dates = [event.date for event in Event.objects.all()]
        self.assertEqual(
            dates,
            [
                # today's event should remain
                initial_event.date,
                datetime.date(2024, 6, 5),
                datetime.date(2024, 6, 12),
                datetime.date(2024, 6, 19),
                datetime.date(2024, 6, 26),
            ],
        )

    @freeze_time("2024-06-01")
    def test_create_series_from_event_tomorrow(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=30),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.WEDNESDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        EventFactory(
            recurring_event=recurring_event,
            date=datetime.date.today() + datetime.timedelta(days=1),
        )
        reschedule(recurring_event)
        dates = [event.date for event in Event.objects.all()]
        self.assertEqual(
            dates,
            [
                # initial event is in future and should be rescheduled
                datetime.date(2024, 6, 5),
                datetime.date(2024, 6, 12),
                datetime.date(2024, 6, 19),
                datetime.date(2024, 6, 26),
            ],
        )

    def test_reschedule_more_events(self):
        with freeze_time("2024-06-01"):
            recurring_event = RecurringEventFactory(
                end_date=datetime.date.today() + datetime.timedelta(days=30),
            )
            rule = RecurrenceRuleFactory(
                weekday=RecurrenceRule.Weekday.WEDNESDAY,
                week=RecurrenceRule.Week.EVERY,
                type=RecurrenceRule.Type.SCHEDULE,
                recurring_event=recurring_event,
            )
            EventFactory(
                recurring_event=recurring_event,
                date=datetime.date.today() + datetime.timedelta(days=1),
            )
            reschedule(recurring_event)
            dates = [event.date for event in Event.objects.all()]
            self.assertEqual(
                dates,
                [
                    datetime.date(2024, 6, 5),
                    datetime.date(2024, 6, 12),
                    datetime.date(2024, 6, 19),
                    datetime.date(2024, 6, 26),
                ],
            )
        with freeze_time("2024-06-15"):
            # 2 weeks later we reschedule the event to Friday and move the end_date to later
            # More future event should be scheduled
            recurring_event.end_date = datetime.date.today() + datetime.timedelta(
                days=30
            )
            rule.weekday = RecurrenceRule.Weekday.FRIDAY
            rule.save()
            reschedule(recurring_event)
            dates = [event.date for event in Event.objects.all()]
            self.assertEqual(
                dates,
                [
                    datetime.date(2024, 6, 5),
                    datetime.date(2024, 6, 12),
                    datetime.date(2024, 6, 21),
                    datetime.date(2024, 6, 28),
                    datetime.date(2024, 7, 5),
                    datetime.date(2024, 7, 12),
                ],
            )

    def test_reschedule_less_events(self):
        with freeze_time("2024-06-01"):
            recurring_event = RecurringEventFactory(
                end_date=datetime.date.today() + datetime.timedelta(days=30),
            )
            rule = RecurrenceRuleFactory(
                weekday=RecurrenceRule.Weekday.WEDNESDAY,
                week=RecurrenceRule.Week.EVERY,
                type=RecurrenceRule.Type.SCHEDULE,
                recurring_event=recurring_event,
            )
            EventFactory(
                recurring_event=recurring_event,
                date=datetime.date.today() + datetime.timedelta(days=1),
            )
            reschedule(recurring_event)
            dates = [event.date for event in Event.objects.all()]
            self.assertEqual(
                dates,
                [
                    datetime.date(2024, 6, 5),
                    datetime.date(2024, 6, 12),
                    datetime.date(2024, 6, 19),
                    datetime.date(2024, 6, 26),
                ],
            )
        with freeze_time("2024-06-07"):
            # a week later we reschedule the event to Monday with a sooner end_date
            # So less future events should be rescheduled
            recurring_event.end_date = datetime.date.today() + datetime.timedelta(
                days=15
            )
            rule.weekday = RecurrenceRule.Weekday.MONDAY
            rule.save()
            reschedule(recurring_event)
            dates = [event.date for event in Event.objects.all()]
            self.assertEqual(
                dates,
                [
                    datetime.date(2024, 6, 5),
                    datetime.date(2024, 6, 10),
                    datetime.date(2024, 6, 17),
                ],
            )

    @freeze_time("2024-06-01")
    def test_schedule_monthly_regional_events(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.FIRST,
            type=RecurrenceRule.Type.REGIONAL,
            recurring_event=recurring_event,
        )
        initial_event = EventFactory(
            recurring_event=recurring_event,
            category=Event.Category.REGULAR,
            date=datetime.date.today(),
        )
        reschedule(recurring_event)
        events = Event.objects.all()
        dates = [event.date for event in events]
        self.assertEqual(
            dates,
            [
                initial_event.date,
                datetime.date(2024, 6, 7),
                datetime.date(2024, 6, 14),
                datetime.date(2024, 6, 21),
                datetime.date(2024, 6, 28),
                datetime.date(2024, 7, 5),
                datetime.date(2024, 7, 12),
                datetime.date(2024, 7, 19),
                datetime.date(2024, 7, 26),
            ],
        )
        categories = [event.category for event in events]
        self.assertEqual(
            categories,
            [
                Event.Category.REGULAR,
                Event.Category.REGIONAL,
                Event.Category.REGULAR,
                Event.Category.REGULAR,
                Event.Category.REGULAR,
                Event.Category.REGIONAL,
                Event.Category.REGULAR,
                Event.Category.REGULAR,
                Event.Category.REGULAR,
            ],
        )

    def test_reschedule_regional(self):
        with freeze_time("2024-06-01"):
            recurring_event = RecurringEventFactory(
                end_date=datetime.date.today() + datetime.timedelta(days=30),
            )
            regular_rule = RecurrenceRuleFactory(
                weekday=RecurrenceRule.Weekday.FRIDAY,
                week=RecurrenceRule.Week.EVERY,
                type=RecurrenceRule.Type.SCHEDULE,
                recurring_event=recurring_event,
            )
            regional_rule = RecurrenceRuleFactory(
                weekday=RecurrenceRule.Weekday.FRIDAY,
                week=RecurrenceRule.Week.FIRST,
                type=RecurrenceRule.Type.REGIONAL,
                recurring_event=recurring_event,
            )
            EventFactory(
                recurring_event=recurring_event,
                category=Event.Category.REGULAR,
                date=datetime.date.today() + datetime.timedelta(days=1),
            )
            reschedule(recurring_event)
            events = Event.objects.all()
            dates = [event.date for event in events]
            self.assertEqual(
                dates,
                [
                    datetime.date(2024, 6, 7),
                    datetime.date(2024, 6, 14),
                    datetime.date(2024, 6, 21),
                    datetime.date(2024, 6, 28),
                ],
            )
            categories = [event.category for event in events]
            self.assertEqual(
                categories,
                [
                    Event.Category.REGIONAL,
                    Event.Category.REGULAR,
                    Event.Category.REGULAR,
                    Event.Category.REGULAR,
                ],
            )
        with freeze_time("2024-06-14"):
            # two weeks later the TO reschedules the event to Wednesday
            recurring_event.end_date = datetime.date.today() + datetime.timedelta(
                days=30
            )
            regular_rule.weekday = RecurrenceRule.Weekday.WEDNESDAY
            regular_rule.save()
            regional_rule.weekday = RecurrenceRule.Weekday.WEDNESDAY
            regional_rule.week = RecurrenceRule.Week.SECOND
            regional_rule.save()
            recurring_event.save()
            reschedule(recurring_event)
            events = Event.objects.all()
            dates = [event.date for event in events]
            categories = [event.category for event in events]
            self.assertEqual(
                dates,
                [
                    datetime.date(2024, 6, 7),
                    datetime.date(2024, 6, 14),
                    datetime.date(2024, 6, 19),
                    datetime.date(2024, 6, 26),
                    datetime.date(2024, 7, 3),
                    datetime.date(2024, 7, 10),
                ],
            )
            self.assertEqual(
                categories,
                [
                    Event.Category.REGIONAL,
                    Event.Category.REGULAR,
                    Event.Category.REGULAR,
                    Event.Category.REGULAR,
                    Event.Category.REGULAR,
                    Event.Category.REGIONAL,
                ],
            )

    @freeze_time("2024-06-01")
    def test_schedule_with_regional_rule_only(self):
        """In case the TO decides to schedule a monthly Regional event without any Regular events in the
        series, they might only create a Regional rule."""
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.FIRST,
            type=RecurrenceRule.Type.REGIONAL,
            recurring_event=recurring_event,
        )
        EventFactory(
            recurring_event=recurring_event,
            category=Event.Category.REGULAR,
            date=datetime.date.today() + datetime.timedelta(days=1),
        )
        reschedule(recurring_event)
        events = Event.objects.all()
        dates = [event.date for event in events]
        self.assertEqual(
            dates,
            [
                datetime.date(2024, 6, 7),
                datetime.date(2024, 7, 5),
            ],
        )
        categories = [event.category for event in events]
        self.assertEqual(
            categories,
            [
                Event.Category.REGIONAL,
                Event.Category.REGIONAL,
            ],
        )
