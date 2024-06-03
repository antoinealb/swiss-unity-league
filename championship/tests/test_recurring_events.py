
import datetime
from django.test import Client, TestCase
from django.contrib.auth.models import User

from championship.factories import RecurrenceRuleFactory, RecurringEventFactory
from championship.models import RecurrenceRule
from championship.views.recurring_events import calculate_recurrence_dates
from freezegun import freeze_time

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
        self.assertEqual(len(dates), 2)
        self.assertEqual(len(regional_dates), 0)
        self.assertEqual(dates[0], datetime.datetime(2024, 6, 7))
        self.assertEqual(dates[1], datetime.datetime(2024, 6, 14))
    

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
        self.assertEqual(len(dates), 4)
        self.assertEqual(dates[0], datetime.datetime(2024, 6, 14))
        self.assertEqual(dates[1], datetime.datetime(2024, 6, 28))
        self.assertEqual(dates[2], datetime.datetime(2024, 7, 12))
        self.assertEqual(dates[3], datetime.datetime(2024, 7, 26))
    
    @freeze_time("2024-06-01")
    def test_recurring_first_monday_and_last_friday_of_month(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.MONDAY,
            week=RecurrenceRule.Week.FIRST,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.LAST,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event
        )
        dates, _ = calculate_recurrence_dates(recurring_event)

        self.assertEqual(len(dates), 4)
        self.assertEqual(dates[0], datetime.datetime(2024, 6, 3))
        self.assertEqual(dates[1], datetime.datetime(2024, 6, 28))
        self.assertEqual(dates[2], datetime.datetime(2024, 7, 1))
        self.assertEqual(dates[3], datetime.datetime(2024, 7, 26))

    @freeze_time("2024-06-01")
    def test_every_friday_except_the_last_of_month(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.LAST,
            type=RecurrenceRule.Type.SKIP,
            recurring_event=recurring_event
        )
        dates, _ = calculate_recurrence_dates(recurring_event)

        self.assertEqual(len(dates), 6)
        self.assertEqual(dates[0], datetime.datetime(2024, 6, 7))
        self.assertEqual(dates[1], datetime.datetime(2024, 6, 14))
        self.assertEqual(dates[2], datetime.datetime(2024, 6, 21))
        self.assertEqual(dates[3], datetime.datetime(2024, 7, 5))
        self.assertEqual(dates[4], datetime.datetime(2024, 7, 12))
        self.assertEqual(dates[5], datetime.datetime(2024, 7, 19))

    
    @freeze_time("2024-06-01")
    def test_every_first_friday_regional(self):
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.FIRST,
            type=RecurrenceRule.Type.REGIONAL,
            recurring_event=recurring_event
        )
        dates, regional_dates = calculate_recurrence_dates(recurring_event)
        self.assertEqual(len(dates), 6)
        self.assertEqual(len(regional_dates), 2)
        self.assertEqual(dates[0], datetime.datetime(2024, 6, 14))
        self.assertEqual(dates[1], datetime.datetime(2024, 6, 21))
        self.assertEqual(dates[2], datetime.datetime(2024, 6, 28))
        self.assertEqual(dates[3], datetime.datetime(2024, 7, 12))
        self.assertEqual(dates[4], datetime.datetime(2024, 7, 19))
        self.assertEqual(dates[5], datetime.datetime(2024, 7, 26))
        self.assertEqual(regional_dates[0], datetime.datetime(2024, 6, 7))
        self.assertEqual(regional_dates[1], datetime.datetime(2024, 7, 5))


    @freeze_time("2024-06-01")
    def test_past_recurrence_dates_are_calculated(self):
        # Even though past events will not be rescheduled, we still need to calculate them for some features
        recurring_event = RecurringEventFactory(
            start_date=datetime.date.today() - datetime.timedelta(days=15),
            end_date=datetime.date.today(),
        )
        RecurrenceRuleFactory(
            weekday=RecurrenceRule.Weekday.FRIDAY,
            week=RecurrenceRule.Week.EVERY,
            type=RecurrenceRule.Type.SCHEDULE,
            recurring_event=recurring_event,
        )
        dates, regional_dates = calculate_recurrence_dates(recurring_event)
        self.assertEqual(len(dates), 3)
        self.assertEqual(len(regional_dates), 0)
        self.assertEqual(dates[0], datetime.datetime(2024, 5, 17))
        self.assertEqual(dates[1], datetime.datetime(2024, 5, 24))
        self.assertEqual(dates[2], datetime.datetime(2024, 5, 31))