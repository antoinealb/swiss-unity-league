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
from django.test import Client, TestCase
from django.urls import reverse

from freezegun import freeze_time

from championship.factories import (
    EventFactory,
    EventPlayerResultFactory,
    RecurrenceRuleFactory,
    RecurringEventFactory,
    UserFactory,
)
from championship.models import Event, RecurrenceRule, RecurringEvent
from championship.views import calculate_recurrence_dates, reschedule


class RecurringEventModelTest(TestCase):

    def test_end_date_one_year_in_future_throw_validation_error(self):
        # We only allow recurring events to be scheduled for up to a year.
        event = RecurringEventFactory(
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=365),
        )
        event.full_clean()
        with self.assertRaises(ValidationError):
            event = RecurringEventFactory(
                end_date=datetime.date.today() + datetime.timedelta(days=366),
            )
            event.full_clean()

    def test_end_date_before_start_date_throw_validation_error(self):
        event = RecurringEventFactory(
            start_date=datetime.date.today(),
            end_date=datetime.date.today(),
        )
        event.full_clean()
        with self.assertRaises(ValidationError):
            event = RecurringEventFactory(
                start_date=datetime.date.today() + datetime.timedelta(days=1),
                end_date=datetime.date.today(),
            )
            event.full_clean()

    def test_start_date_older_one_year_throw_validation_error(self):
        event = RecurringEventFactory(
            start_date=datetime.date.today() - datetime.timedelta(days=366),
            end_date=datetime.date.today(),
        )
        # Allow leaving start_date the same
        event.full_clean()
        with self.assertRaises(ValidationError):
            # But not changing it to a date older than a year
            event.start_date = datetime.date.today() - datetime.timedelta(days=367)
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
        dates, regional_dates = calculate_recurrence_dates(recurring_event)

        self.assertEqual(
            dates,
            [
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

        self.assertEqual(
            regional_dates,
            [
                datetime.date(2024, 6, 7),
                datetime.date(2024, 7, 5),
            ],
        )

    @freeze_time("2024-06-01")
    def test_past_recurrence_dates_calculated(self):
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
                datetime.date(2024, 5, 17),
                datetime.date(2024, 5, 24),
                datetime.date(2024, 5, 31),
                datetime.date(2024, 6, 7),
            ],
        )
        self.assertEqual(regional_dates, [])


class RecurrenceEventCreationTest(TestCase):

    def test_recurring_event_without_linked_event_throws_error(self):
        recurring_event = RecurringEventFactory()
        with self.assertRaises(ValueError):
            reschedule(recurring_event)

    @freeze_time("2024-06-01")
    def test_create_series(self):
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
            date=datetime.date.today(),
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

    @freeze_time("2024-06-01")
    def test_create_series_from_event_with_results(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=30),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.WEDNESDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        event = EventFactory(
            recurring_event=recurring_event,
            date=datetime.date.today(),
        )
        EventPlayerResultFactory(event=event)
        reschedule(recurring_event)
        dates = [event.date for event in Event.objects.all()]
        self.assertEqual(
            dates,
            [
                # event with results should remain
                event.date,
                datetime.date(2024, 6, 5),
                datetime.date(2024, 6, 12),
                datetime.date(2024, 6, 19),
                datetime.date(2024, 6, 26),
            ],
        )

    def test_reschedule_more_events(self):
        """Test that we can reschedule more events than before.
        - We create a series of events on Wednesdays for a month.
        - After 2 weeks we reschedule the series to Fridays for another month.
        """
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
                    datetime.date(2024, 6, 7),
                    datetime.date(2024, 6, 14),
                    datetime.date(2024, 6, 21),
                    datetime.date(2024, 6, 28),
                    datetime.date(2024, 7, 5),
                    datetime.date(2024, 7, 12),
                ],
            )

    def test_reschedule_less_events(self):
        """Test that we can reschedule less events than before.
        - We create a series of events on Wednesdays for a month.
        - After 2 weeks we reschedule the series to Mondays for another month."""
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
                    datetime.date(2024, 6, 3),
                    datetime.date(2024, 6, 10),
                    datetime.date(2024, 6, 17),
                ],
            )

    @freeze_time("2024-06-01")
    def test_schedule_monthly_regional_events(self):
        """Test that we can create a series of events on Fridays for 2 months, where the first Friday is Regional.
        - We do this by creating a RecurrenceRule to schedule the event for every Friday.
        - We create another one for the first Friday of the month as Regional.
        """
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
        EventFactory(
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
        """Test that we can reschedule a series of events with Regional events.
        - We create a series of events on Fridays for a month, where the first Friday is Regional.
        - After 2 weeks we reschedule the series to Wednesdays for another month and move the Regional to the second week.
        """
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
                    datetime.date(2024, 6, 5),
                    datetime.date(2024, 6, 12),
                    datetime.date(2024, 6, 19),
                    datetime.date(2024, 6, 26),
                    datetime.date(2024, 7, 3),
                    datetime.date(2024, 7, 10),
                ],
            )
            self.assertEqual(
                categories,
                [
                    Event.Category.REGULAR,
                    Event.Category.REGIONAL,
                    Event.Category.REGULAR,
                    Event.Category.REGULAR,
                    Event.Category.REGULAR,
                    Event.Category.REGIONAL,
                ],
            )

    def test_reschedule_preserves_pk(self):
        """
        The primary keys of the events should be reused if the event takes place in the same week.
        This makes sure the links to the events are preserved.
        - We create a series of events on Wednesdays for a month.
        - After 2 weeks we move the series by a month and set the day to Fridays.
        - Since the 3rd and 4th event are in the same week as the newly scheduled events, their primary keys should be preserved.
        """
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
                date=datetime.date.today(),
            )
            reschedule(recurring_event)
            events = Event.objects.all()
            pks = [event.pk for event in events]
            self.assertEqual(pks, [2, 3, 4, 5])
        with freeze_time("2024-06-15"):
            # 2 weeks later we reschedule the event to Friday for another month
            recurring_event.start_date = datetime.date.today()
            recurring_event.end_date = datetime.date.today() + datetime.timedelta(
                days=30
            )
            rule.weekday = RecurrenceRule.Weekday.FRIDAY
            rule.save()
            reschedule(recurring_event)
            events = Event.objects.all()
            pks = [event.pk for event in events]
            # the primary key of the 3rd and 4th event are preserved, because they are in the same week
            # as the newly scheduled events
            self.assertEqual(pks, [4, 5, 6, 7])

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
            date=datetime.date.today(),
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


class RecurringEventViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.force_login(UserFactory())
        self.data = {
            "start_date": "2024-06-01",
            "end_date": "2024-06-30",
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 1,
            "form-MAX_NUM_FORMS": 10,
            "form-0-weekday": RecurrenceRule.Weekday.FRIDAY,
            "form-0-week": RecurrenceRule.Week.EVERY,
            "form-0-type": RecurrenceRule.Type.SCHEDULE,
        }

    def test_get_create_recurring_event(self):
        response = self.client.get(reverse("recurring_event_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, RecurrenceRule.Weekday.FRIDAY.name)
        self.assertContains(response, RecurrenceRule.Week.EVERY.name)
        self.assertContains(response, RecurrenceRule.Type.SCHEDULE.name)

    def test_create_recurring_event(self):

        response = self.client.post(reverse("recurring_event_create"), self.data)
        self.assertEqual(response.status_code, 302)

        recurring_event = RecurringEvent.objects.first()
        self.assertEqual(recurring_event.start_date, datetime.date(2024, 6, 1))
        self.assertEqual(recurring_event.end_date, datetime.date(2024, 6, 30))
        self.assertEqual(recurring_event.recurrencerule_set.count(), 1)

        rule = recurring_event.recurrencerule_set.first()
        self.assertEqual(rule.weekday, RecurrenceRule.Weekday.FRIDAY)
        self.assertEqual(rule.week, RecurrenceRule.Week.EVERY)
        self.assertEqual(rule.type, RecurrenceRule.Type.SCHEDULE)
        self.assertEqual(rule.recurring_event, recurring_event)

    def test_get_update_recurring_event(self):
        recurring_event = RecurringEventFactory()
        rule = RecurrenceRuleFactory(recurring_event=recurring_event)
        response = self.client.get(
            reverse("recurring_event_update", args=[recurring_event.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, rule.weekday)
        self.assertContains(response, rule.week)
        self.assertContains(response, rule.type)

    def test_update_recurring_event(self):
        recurring_event = RecurringEventFactory()
        old_rule = RecurrenceRuleFactory(recurring_event=recurring_event)
        response = self.client.post(
            reverse("recurring_event_update", args=[recurring_event.id]), self.data
        )
        self.assertEqual(response.status_code, 302)

        recurring_event.refresh_from_db()
        self.assertEqual(recurring_event.start_date, datetime.date(2024, 6, 1))
        self.assertEqual(recurring_event.end_date, datetime.date(2024, 6, 30))
        self.assertEqual(recurring_event.recurrencerule_set.count(), 1)

        rule = recurring_event.recurrencerule_set.first()
        self.assertEqual(rule.weekday, RecurrenceRule.Weekday.FRIDAY)
        self.assertEqual(rule.week, RecurrenceRule.Week.EVERY)
        self.assertEqual(rule.type, RecurrenceRule.Type.SCHEDULE)
