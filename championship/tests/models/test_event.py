from unittest.mock import patch
from parameterized import parameterized
from championship.models import Event
from championship.factories import EventFactory
from django.test import TestCase
import datetime
from datetime import date

from mtg_championship_site import settings


class EventCanChangeResults(TestCase):
    @parameterized.expand([(2, True), (10, True), (32, False)])
    def test_can_change_based_on_date(self, age_days, want_can_change):
        d = datetime.date.today() - datetime.timedelta(days=age_days)
        e = EventFactory(date=d)
        self.assertEqual(e.can_be_edited(), want_can_change)

    @parameterized.expand(
        [
            # Season 1
            (date(2023, 10, 31), date(2023, 11, 8), False),
            (date(2023, 10, 31), date(2023, 10, 31), True),
            (date(2023, 10, 31), date(2023, 11, 7), True),
            (date(2023, 10, 6), date(2023, 11, 7), False),
            # Season 2
            (date(2023, 11, 1), date(2023, 11, 8), True),
            (date(2023, 11, 1), date(2024, 11, 7), False),
            # Completely out of season
            (date(2019, 11, 1), date(2019, 11, 2), False),
        ]
    )
    @patch("championship.models.datetime")
    @patch("mtg_championship_site.settings.datetime")
    def test_can_change_based_on_season_deadline(
        self,
        event_date,
        today,
        want_can_change,
        mock_datetime_settings,
        mock_datetime_models,
    ):
        mock_datetime_models.date.today.return_value = today
        mock_datetime_settings.date.today.return_value = today

        e = EventFactory(date=event_date)
        self.assertEqual(
            e.can_be_edited(),
            want_can_change,
        )
