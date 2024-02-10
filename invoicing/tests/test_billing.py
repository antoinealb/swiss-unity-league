import datetime
from championship.factories import *
from championship.models import *
from django.test import TestCase
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
            EventPlayerResultFactory(event=e)

        self.assert_fee_for_event(20, e)

    def test_bill_regional_top(self):
        e = EventFactory(category=Event.Category.REGIONAL)

        EventPlayerResultFactory(
            event=e,
            single_elimination_result=EventPlayerResult.SingleEliminationResult.WINNER,
        )
        for _ in range(9):
            EventPlayerResultFactory(event=e)

        self.assert_fee_for_event(35, e)

    def test_bill_premier(self):
        e = EventFactory(category=Event.Category.PREMIER)

        EventPlayerResultFactory(
            event=e,
            single_elimination_result=EventPlayerResult.SingleEliminationResult.WINNER,
        )
        for _ in range(9):
            EventPlayerResultFactory(event=e)

        self.assert_fee_for_event(105, e)


class Billing2024FeesTestCase(BillingTestCase):
    def test_bill_for_regional_no_top(self):
        e = Event2024Factory(category=Event.Category.REGIONAL)
        for _ in range(10):
            EventPlayerResultFactory(event=e)

        self.assert_fee_for_event(10, e)

    def test_bill_regional_top(self):
        e = Event2024Factory(category=Event.Category.REGIONAL)

        EventPlayerResultFactory(
            event=e,
            single_elimination_result=EventPlayerResult.SingleEliminationResult.WINNER,
        )
        for _ in range(9):
            EventPlayerResultFactory(event=e)

        self.assert_fee_for_event(30, e)

    def test_bill_premier(self):
        e = Event2024Factory(category=Event.Category.PREMIER)

        EventPlayerResultFactory(
            event=e,
            single_elimination_result=EventPlayerResult.SingleEliminationResult.WINNER,
        )
        for _ in range(9):
            EventPlayerResultFactory(event=e)

        self.assert_fee_for_event(120, e)


class BillingNoSeasonRaisesRuntimeError(BillingTestCase):
    def test_no_season_prices(self):
        e = EventFactory(
            category=Event.Category.REGIONAL, date=datetime.date(2000, 1, 1)
        )
        with self.assertRaises(ValueError):
            fee_for_event(e)
