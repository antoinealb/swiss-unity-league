from parameterized import parameterized
from championship.models import Event
from championship.factories import EventFactory
from django.test import TestCase
import datetime


class EventCanChangeResults(TestCase):
    @parameterized.expand([(2, True), (10, True), (32, False)])
    def test_can_change_based_on_date(self, age_days, want_can_change):
        d = datetime.date.today() - datetime.timedelta(days=age_days)
        e = EventFactory(date=d)
        self.assertEqual(e.can_be_edited(), want_can_change)
