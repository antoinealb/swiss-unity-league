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

from django.test import TestCase

from championship.factories import (
    Event2024Factory,
    Event2025Factory,
    EventFactory,
    ResultFactory,
)
from championship.models import Event, Result
from invoicing.models import fee_for_event


class BillingTestCase(TestCase):
    def assert_fee_for_event(self, fee: int, event: Event):
        self.assertEqual(
            fee, fee_for_event(event), f"Fee for '{event}' should be {fee}"
        )


class Billing2023TestCase(BillingTestCase):
    def test_bill_for_regular_is_free(self):
        e = EventFactory(category=Event.Category.REGULAR)
        self.assert_fee_for_event(0, e)

    def test_bill_for_regional_no_top(self):
        e = EventFactory(category=Event.Category.REGIONAL)
        for _ in range(10):
            ResultFactory(event=e)

        self.assert_fee_for_event(20, e)

    def test_bill_regional_top(self):
        e = EventFactory(category=Event.Category.REGIONAL)

        ResultFactory(
            event=e,
            playoff_result=Result.PlayoffResult.WINNER,
        )
        for _ in range(9):
            ResultFactory(event=e)

        self.assert_fee_for_event(35, e)

    def test_bill_premier(self):
        e = EventFactory(category=Event.Category.PREMIER)

        ResultFactory(
            event=e,
            playoff_result=Result.PlayoffResult.WINNER,
        )
        for _ in range(9):
            ResultFactory(event=e)

        self.assert_fee_for_event(105, e)


class Billing2024FeesTestCase(BillingTestCase):
    def test_bill_for_regional_no_top(self):
        e = Event2024Factory(category=Event.Category.REGIONAL)
        for _ in range(10):
            ResultFactory(event=e)

        self.assert_fee_for_event(10, e)

    def test_bill_regional_top(self):
        e = Event2024Factory(category=Event.Category.REGIONAL)

        ResultFactory(
            event=e,
            playoff_result=Result.PlayoffResult.WINNER,
        )
        for _ in range(9):
            ResultFactory(event=e)

        self.assert_fee_for_event(30, e)

    def test_bill_premier(self):
        e = Event2024Factory(category=Event.Category.PREMIER)

        ResultFactory(
            event=e,
            playoff_result=Result.PlayoffResult.WINNER,
        )
        for _ in range(9):
            ResultFactory(event=e)

        self.assert_fee_for_event(120, e)


class Billing2025FeesTestCase(BillingTestCase):
    def test_bill_for_regional_no_top(self):
        e = Event2025Factory(category=Event.Category.REGIONAL)
        for _ in range(10):
            ResultFactory(event=e)
        self.assert_fee_for_event(10, e)

    def test_bill_regional_top(self):
        e = Event2025Factory(category=Event.Category.REGIONAL)

        ResultFactory(
            event=e,
            playoff_result=Result.PlayoffResult.WINNER,
        )
        for _ in range(9):
            ResultFactory(event=e)

        self.assert_fee_for_event(30, e)

    def test_bill_premier(self):
        e = Event2025Factory(category=Event.Category.PREMIER)

        ResultFactory(
            event=e,
            playoff_result=Result.PlayoffResult.WINNER,
        )
        for _ in range(9):
            ResultFactory(event=e)

        self.assert_fee_for_event(200, e)


class BillingNoSeasonRaisesRuntimeError(BillingTestCase):
    def test_no_season_prices(self):
        e = EventFactory(
            category=Event.Category.REGIONAL, date=datetime.date(2000, 1, 1)
        )
        with self.assertRaises(ValueError):
            fee_for_event(e)
