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
    RecurrenceRuleFactory,
    RecurringEventFactory,
    ResultFactory,
    UserFactory,
)
from championship.models import Event, RecurrenceRule, RecurringEvent
from championship.views import calculate_recurrence_dates, reschedule
from championship.views.recurring_events import NoDatesError


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
        ResultFactory(event=event)
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

    @freeze_time("2024-06-01")
    def test_event_with_results_shouldnt_be_scheduled_twice(self):
        """When we schedule an event series, add results to a few events and then reschedule the series,
        the events with results should remain the same and not be duplicated/rescheduled.
        """
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
        reschedule(recurring_event)
        events = Event.objects.all()
        # add results to the first 3 events
        results = [ResultFactory(event=event) for event in events[:3]]
        reschedule(recurring_event)
        events = Event.objects.all()
        dates = [event.date for event in events]
        self.assertEqual(
            dates,
            [
                datetime.date(2024, 6, 5),
                datetime.date(2024, 6, 12),
                datetime.date(2024, 6, 19),
                datetime.date(2024, 6, 26),
            ],
        )
        for index, result in enumerate(results):
            event = events[index]
            results_of_event = event.result_set.all()
            self.assertEqual(len(results_of_event), 1)
            self.assertEqual(results_of_event[0], result)

    def test_reschedule_doesnt_copy_admin_fields(self):
        """Admin fields of event should not be updated when we reschedule an event."""
        recurring_event = RecurringEventFactory(
            start_date=datetime.date.today() - datetime.timedelta(days=7),
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
            results_validation_enabled=False,
            include_in_invoices=False,
            edit_deadline_override=datetime.date.today(),
        )
        reschedule(recurring_event)
        events = Event.objects.all()
        for event in events:
            # Check that only the initial_event keeps the admin fields
            self.assertEqual(
                event.results_validation_enabled, initial_event.pk != event.pk
            )
            self.assertEqual(event.include_in_invoices, initial_event.pk != event.pk)
            self.assertEqual(
                event.edit_deadline_override,
                (
                    None
                    if initial_event.pk != event.pk
                    else initial_event.edit_deadline_override
                ),
            )

            # The other fields should be the same for all events
            self.assertEqual(event.organizer, initial_event.organizer)
            self.assertEqual(event.recurring_event, initial_event.recurring_event)
            self.assertEqual(event.name, initial_event.name)
            self.assertEqual(event.url, initial_event.url)
            self.assertEqual(event.category, initial_event.category)
            self.assertEqual(event.format, initial_event.format)

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
        self.data = {
            "name": "Test Event Series",
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
        self.event = EventFactory()
        self.client.force_login(self.event.organizer.user)

    @freeze_time("2024-06-01")
    def test_get_create_recurring_event(self):
        response = self.client.get(
            reverse("recurring_event_create", args=[self.event.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, RecurrenceRule.Weekday.FRIDAY.name)
        self.assertContains(response, RecurrenceRule.Week.EVERY.name)
        self.assertContains(response, RecurrenceRule.Type.SCHEDULE.name)
        self.assertContains(response, "Create Event Series")

    def test_unauthorized_user_cannot_create_recurring_event(self):
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.get(
            reverse("recurring_event_create", args=[self.event.id])
        )
        self.assertEqual(response.status_code, 403)

    @freeze_time("2024-06-01")
    def test_create_recurring_event(self):

        response = self.client.post(
            reverse("recurring_event_create", args=[self.event.id]), self.data
        )
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

        event_dates = [event.date for event in Event.objects.all()]

        self.assertEqual(
            event_dates,
            [
                datetime.date(2024, 6, 7),
                datetime.date(2024, 6, 14),
                datetime.date(2024, 6, 21),
                datetime.date(2024, 6, 28),
            ],
        )

    @freeze_time("2024-06-01")
    def test_get_update_recurring_event(self):
        recurring_event = RecurringEventFactory()
        self.event.recurring_event = recurring_event
        self.event.save()
        rule = RecurrenceRuleFactory(recurring_event=recurring_event)
        response = self.client.get(
            reverse("recurring_event_update", args=[recurring_event.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, rule.weekday)
        self.assertContains(response, rule.week)
        self.assertContains(response, rule.type)
        self.assertContains(response, "Update Schedule of Event Series")

    @freeze_time("2024-06-01")
    def test_update_recurring_event(self):
        recurring_event = RecurringEventFactory()
        self.event.recurring_event = recurring_event
        self.event.save()

        old_rule = RecurrenceRuleFactory(recurring_event=recurring_event)
        self.data["form-TOTAL_FORMS"] = 2
        self.data["form-1-weekday"] = RecurrenceRule.Weekday.FRIDAY
        self.data["form-1-week"] = RecurrenceRule.Week.FIRST
        self.data["form-1-type"] = RecurrenceRule.Type.REGIONAL
        response = self.client.post(
            reverse("recurring_event_update", args=[recurring_event.id]), self.data
        )
        self.assertEqual(response.status_code, 302)

        recurring_event.refresh_from_db()
        self.assertEqual(recurring_event.start_date, datetime.date(2024, 6, 1))
        self.assertEqual(recurring_event.end_date, datetime.date(2024, 6, 30))
        rules = recurring_event.recurrencerule_set.all()
        self.assertEqual(len(rules), 2)
        rule = rules[0]
        self.assertEqual(rule.weekday, RecurrenceRule.Weekday.FRIDAY)
        self.assertEqual(rule.week, RecurrenceRule.Week.EVERY)
        self.assertEqual(rule.type, RecurrenceRule.Type.SCHEDULE)
        rule = rules[1]
        self.assertEqual(rule.weekday, RecurrenceRule.Weekday.FRIDAY)
        self.assertEqual(rule.week, RecurrenceRule.Week.FIRST)
        self.assertEqual(rule.type, RecurrenceRule.Type.REGIONAL)

        with self.assertRaises(RecurrenceRule.DoesNotExist):
            old_rule.refresh_from_db()

        events = Event.objects.all()
        event_dates = [event.date for event in events]
        event_categories = [event.category for event in events]
        self.assertEqual(
            event_dates,
            [
                datetime.date(2024, 6, 7),
                datetime.date(2024, 6, 14),
                datetime.date(2024, 6, 21),
                datetime.date(2024, 6, 28),
            ],
        )
        self.assertEqual(
            event_categories,
            [
                Event.Category.REGIONAL,
                Event.Category.REGULAR,
                Event.Category.REGULAR,
                Event.Category.REGULAR,
            ],
        )

    def test_unauthorized_user_cannot_update_recurring_event(self):
        user = UserFactory()
        self.client.force_login(user)
        recurring_event = RecurringEventFactory()
        self.event.recurring_event = recurring_event
        self.event.save()
        response = self.client.get(
            reverse("recurring_event_update", args=[recurring_event.id])
        )
        self.assertEqual(response.status_code, 403)

    def test_forbid_create_second_recurring_event(self):
        """When an event already has a recurring event, we should not allow creating another one."""
        recurring_event = RecurringEventFactory()
        self.event.recurring_event = recurring_event
        self.event.save()
        response = self.client.post(
            reverse("recurring_event_create", args=[self.event.id]), self.data
        )
        self.assertEqual(response.status_code, 403)

    def test_create_recurring_event_without_dates(self):
        # RecurringEvent is only 1 day long and Friday doesn't occur on that day.
        self.data["end_date"] = "2024-06-01"
        response = self.client.post(
            reverse("recurring_event_create", args=[self.event.id]), self.data
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, NoDatesError.ui_message)
        # No recurring event was created
        self.assertEqual(RecurringEvent.objects.count(), 0)

    @freeze_time("2024-06-01")
    def test_copy_recurring_event(self):
        # Create a recurring event every wednesday for May
        recurring_event1 = RecurringEventFactory(
            start_date=datetime.date(2024, 5, 1),
            end_date=datetime.date(2024, 5, 31),
        )
        rule = RecurrenceRuleFactory(
            recurring_event=recurring_event1,
            weekday=RecurrenceRule.Weekday.WEDNESDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
        )
        self.event.recurring_event = recurring_event1
        self.event.save()
        reschedule(recurring_event1)

        # Copy the recurring event to June but this time on Fridays
        response = self.client.post(
            reverse("recurring_event_copy", args=[recurring_event1.id]), self.data
        )
        self.assertEqual(response.status_code, 302)
        event_dates = [event.date for event in Event.objects.all()]
        self.assertEqual(
            event_dates,
            [
                datetime.date(2024, 5, 1),
                datetime.date(2024, 5, 8),
                datetime.date(2024, 5, 15),
                datetime.date(2024, 5, 22),
                datetime.date(2024, 5, 29),
                datetime.date(2024, 6, 7),
                datetime.date(2024, 6, 14),
                datetime.date(2024, 6, 21),
                datetime.date(2024, 6, 28),
            ],
        )
        recurring_events = RecurringEvent.objects.all()
        self.assertEqual(len(recurring_events), 2)
        recurring_event1 = recurring_events[0]
        self.assertEqual(recurring_event1.start_date, datetime.date(2024, 5, 1))
        self.assertEqual(recurring_event1.end_date, datetime.date(2024, 5, 31))
        recurring_event2 = recurring_events[1]
        self.assertEqual(recurring_event2.start_date, datetime.date(2024, 6, 1))
        self.assertEqual(recurring_event2.end_date, datetime.date(2024, 6, 30))
        rules = RecurrenceRule.objects.all()
        self.assertEqual(len(rules), 2)
        rule1 = rules[0]
        self.assertEqual(rule1.weekday, RecurrenceRule.Weekday.WEDNESDAY)
        self.assertEqual(rule1.week, RecurrenceRule.Week.EVERY)
        self.assertEqual(rule1.type, RecurrenceRule.Type.SCHEDULE)
        self.assertEqual(rule1.recurring_event, recurring_event1)
        rule2 = rules[1]
        self.assertEqual(rule2.weekday, RecurrenceRule.Weekday.FRIDAY)
        self.assertEqual(rule2.week, RecurrenceRule.Week.EVERY)
        self.assertEqual(rule2.type, RecurrenceRule.Type.SCHEDULE)
        self.assertEqual(rule2.recurring_event, recurring_event2)


class RecurringEventDeleteViewTest(TestCase):

    def setUp(self):
        self.recurring_event = RecurringEventFactory()
        self.event = EventFactory(recurring_event=self.recurring_event)
        self.client.force_login(self.event.organizer.user)

    def test_can_delete_own_recurring_event(self):
        response = self.client.post(
            reverse("recurring_event_delete", args=[self.recurring_event.id])
        )
        self.assertEqual(response.status_code, 302)

        with self.assertRaises(RecurringEvent.DoesNotExist):
            self.recurring_event.refresh_from_db()

        with self.assertRaises(Event.DoesNotExist):
            self.event.refresh_from_db()

    def test_cannot_delete_other_recurring_event(self):
        self.client.force_login(UserFactory())
        response = self.client.post(
            reverse("recurring_event_delete", args=[self.recurring_event.id])
        )
        self.assertEqual(response.status_code, 403)

        self.recurring_event.refresh_from_db()
        self.event.refresh_from_db()

    def test_events_with_results_are_not_deleted(self):
        ResultFactory(event=self.event)
        response = self.client.post(
            reverse("recurring_event_delete", args=[self.recurring_event.id])
        )
        self.assertEqual(response.status_code, 302)

        with self.assertRaises(RecurringEvent.DoesNotExist):
            self.recurring_event.refresh_from_db()

        self.event.refresh_from_db()


class RecurringEventEditAllTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.recurring_event = RecurringEventFactory()
        self.event = EventFactory(
            recurring_event=self.recurring_event, date=datetime.date.today()
        )
        self.client.force_login(self.event.organizer.user)
        self.data = {
            "name": "Test Event",
            "url": "https://test.example",
            "format": "LEGACY",
            "description": "Test Description",
        }
        self.url = reverse("event_update_all", args=[self.event.id])

    def test_unauthorized_user_cannot_edit_all_events(self):
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_cannot_edit_all_events_without_linked_recurring_event(self):
        self.event.recurring_event = None
        self.event.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_edit_all_events(self):
        response = self.client.post(
            self.url,
            self.data,
        )
        self.assertEqual(response.status_code, 302)

        event = Event.objects.get(pk=self.event.pk)
        self.assertEqual(event.name, self.data["name"])
        self.assertEqual(event.url, self.data["url"])
        self.assertEqual(event.format, self.data["format"])

        # date and category should stay the same
        self.assertEqual(event.category, self.event.category)
        self.assertEqual(event.date, self.event.date)

    def test_not_edit_events_with_results(self):
        """Events with results should not change when editing all events."""
        ResultFactory(event=self.event)
        event_without_results = EventFactory(recurring_event=self.recurring_event)
        response = self.client.post(
            self.url,
            self.data,
        )
        self.assertEqual(response.status_code, 302)

        events = Event.objects.all()
        self.assertEqual(len(events), 2)

        # Event with results should stay the same
        event_with_result = events[0]
        self.assertEqual(event_with_result.name, self.event.name)
        self.assertEqual(event_with_result.url, self.event.url)
        self.assertEqual(event_with_result.format, self.event.format)
        self.assertEqual(event_with_result.description, self.event.description)
        self.assertEqual(event_with_result.category, self.event.category)
        self.assertEqual(event_with_result.date, self.event.date)

        # Event without results should be updated
        updated_event_without_results = events[1]
        self.assertEqual(updated_event_without_results.name, self.data["name"])
        self.assertEqual(updated_event_without_results.url, self.data["url"])
        self.assertEqual(updated_event_without_results.format, self.data["format"])
        # date and category should be the same as before
        self.assertEqual(
            updated_event_without_results.category, event_without_results.category
        )
        self.assertEqual(updated_event_without_results.date, event_without_results.date)

    def test_admin_fields_not_updated(self):
        """Admin fields of event should not be updated when editing all events."""
        self.event.results_validation_enabled = False
        self.event.include_in_invoices = False
        self.event.edit_deadline_override = datetime.date.today()
        self.event.save()
        other_event = EventFactory(recurring_event=self.recurring_event)
        response = self.client.post(
            self.url,
            self.data,
        )
        self.assertEqual(response.status_code, 302)
        # admin fields should not be updated
        other_event.refresh_from_db()
        self.assertTrue(other_event.results_validation_enabled)
        self.assertTrue(other_event.include_in_invoices)
        self.assertIsNone(other_event.edit_deadline_override)

    def test_redirect_to_latest_event(self):
        recurring_event = RecurringEventFactory()
        event = EventFactory(recurring_event=recurring_event)
