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
import re
from datetime import date

from django.conf import settings
from django.test import TestCase

from freezegun import freeze_time
from parameterized import parameterized

from championship.factories import EventFactory, ResultFactory
from championship.models import Event


class EventCopyFromTest(TestCase):

    def setUp(self):
        self.event = None

    def test_admin_fields_and_pk_not_copied(self):
        event: Event = EventFactory(
            results_validation_enabled=False,
            include_in_invoices=False,
            edit_deadline_override=datetime.date.today(),
        )

        copied_event = Event().copy_values_from(event)
        self.assertIsNone(copied_event.pk)
        self.assertTrue(copied_event.results_validation_enabled)
        self.assertTrue(copied_event.include_in_invoices)
        self.assertIsNone(copied_event.edit_deadline_override)

        fields_not_copied = [
            "pk",
            "id",
            "results_validation_enabled",
            "include_in_invoices",
            "edit_deadline_override",
        ]
        for field in event._meta.fields:
            if field.name not in fields_not_copied:
                self.assertEqual(
                    getattr(copied_event, field.name), getattr(event, field.name)
                )


class EventCanChangeResults(TestCase):
    @parameterized.expand([(2, True), (10, True), (32, False)])
    @freeze_time("2023-10-20")
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
            (date(2019, 11, 1), date(2019, 11, 2), True),
        ]
    )
    def test_can_change_based_on_season_deadline(
        self,
        event_date,
        today,
        want_can_change,
    ):
        e = EventFactory(date=event_date)
        with freeze_time(today):
            self.assertEqual(
                e.can_be_edited(),
                want_can_change,
            )

    @freeze_time("2023-09-30")
    def test_edit_deadline_override(self):
        e = EventFactory(date=date(2023, 8, 29))
        self.assertEqual(e.can_be_edited(), False)

        e.edit_deadline_override = date(2023, 9, 29)
        self.assertEqual(e.can_be_edited(), False)

        e.edit_deadline_override = date(2023, 9, 30)
        self.assertEqual(e.can_be_edited(), True)


class PremierEventDowngrade(TestCase):
    f"""Premier events with less than {settings.MIN_PLAYERS_FOR_PREMIER} are downgraded to SUL Regional."""

    def setUp(self):
        self.original_name = "Original name"
        self.original_description = "Original description"

    def test_premier_event_downgraded_to_regional(self):
        event = EventFactory(
            category=Event.Category.PREMIER,
            name=self.original_name,
            description=self.original_description,
        )
        event.save()
        self.assertEqual(event.name, self.original_name)
        self.assertEqual(event.description, self.original_description)
        self.assertEqual(event.category, Event.Category.PREMIER)

        for i in range(settings.MIN_PLAYERS_FOR_PREMIER - 1):
            ResultFactory(event=event)

        event.save()
        self.assertEqual(
            event.name, self.original_name + Event.DOWNGRADED_TO_REGIONAL_NAME
        )
        self.assertTrue(Event.DOWNGRADED_TO_REGIONAL_DESCRIPTION in event.description)
        self.assertTrue(self.original_description in event.description)
        self.assertEqual(event.category, Event.Category.REGIONAL)

    def test_premier_with_enough_players_not_downgraded(self):
        event = EventFactory(
            category=Event.Category.PREMIER,
            name=self.original_name,
            description=self.original_description,
        )

        for i in range(settings.MIN_PLAYERS_FOR_PREMIER):
            ResultFactory(event=event)

        event.save()
        self.assertEqual(event.name, self.original_name)
        self.assertEqual(event.description, self.original_description)
        self.assertEqual(event.category, Event.Category.PREMIER)

    def test_edit_to_premier(self):
        """When the event is downgraded to Regional, the TO might think it's a mistake and try to fix it by
        editing the event to Premier. We need to check that the event is correctly downgraded again.
        """
        event = EventFactory(
            category=Event.Category.PREMIER,
            name=self.original_name,
            description=self.original_description,
        )
        ResultFactory(event=event)
        event.save()
        event.category = Event.Category.PREMIER
        event.save()
        self.assertEqual(
            event.name, self.original_name + Event.DOWNGRADED_TO_REGIONAL_NAME
        )
        self.assertEqual(
            len(
                re.findall(Event.DOWNGRADED_TO_REGIONAL_DESCRIPTION, event.description)
            ),
            1,
        )
        self.assertTrue(self.original_description in event.description)
        self.assertEqual(event.category, Event.Category.REGIONAL)

    def test_long_name_truncated(self):
        name_max_length = Event.name.field.max_length
        self.original_name = (self.original_name * 20)[
            :name_max_length
        ]  # Name with max allowed characters
        event = EventFactory(
            category=Event.Category.PREMIER,
            name=self.original_name,
            description=self.original_description,
        )
        ResultFactory(event=event)
        event.save()
        remaining_chars_name = name_max_length - len(Event.DOWNGRADED_TO_REGIONAL_NAME)
        self.assertEqual(
            event.name,
            self.original_name[:remaining_chars_name]
            + Event.DOWNGRADED_TO_REGIONAL_NAME,
        )
        self.assertEqual(
            len(
                re.findall(Event.DOWNGRADED_TO_REGIONAL_DESCRIPTION, event.description)
            ),
            1,
        )
        self.assertTrue(self.original_description in event.description)
        self.assertEqual(event.category, Event.Category.REGIONAL)
