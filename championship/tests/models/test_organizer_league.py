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

from parameterized import parameterized

from championship.factories import (
    OrganizerLeagueFactory,
    RankedEventFactory,
    ResultFactory,
)
from championship.models import Event, OrganizerLeague, Result


class OrganizerLeagueTest(TestCase):

    def test_get_results_for_all_formats(self):
        league = OrganizerLeagueFactory(
            format=OrganizerLeague.Format.All_FORMATS,
        )

        result = ResultFactory(
            event=RankedEventFactory(
                organizer=league.organizer,
                category=league.category,
            )
        )

        results = league.get_results()
        self.assertEqual(results.first(), result)

    def test_get_results_format_specific(self):
        league = OrganizerLeagueFactory(
            format=Event.Format.MODERN,
        )

        result = ResultFactory(
            event=RankedEventFactory(
                format=league.format,
                organizer=league.organizer,
                category=league.category,
            )
        )

        result_of_wrong_format = ResultFactory(
            event=RankedEventFactory(
                format=Event.Format.STANDARD,
                organizer=league.organizer,
                category=league.category,
            )
        )

        results = league.get_results()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], result)

    @parameterized.expand(
        [
            (Event.Category.PREMIER, 3),
            (Event.Category.REGIONAL, 2),
            (Event.Category.REGULAR, 1),
        ]
    )
    def test_get_results_category_specific(self, league_category, num_results):
        """We get results of this category and lower categories."""
        league = OrganizerLeagueFactory(category=league_category)

        for event_category, _ in Event.Category.choices:
            result = ResultFactory(
                event=RankedEventFactory(
                    format=league.format,
                    organizer=league.organizer,
                    category=event_category,
                )
            )

        results = league.get_results()
        self.assertEqual(len(results), num_results)

    def test_get_results_within_date_range(self):
        league = OrganizerLeagueFactory(
            start_date=datetime.date(2024, 7, 1),
            end_date=datetime.date(2024, 7, 31),
        )
        for date in [
            datetime.date(2024, 6, 30),
            datetime.date(2024, 7, 1),
            datetime.date(2024, 7, 31),
            datetime.date(2024, 8, 1),
        ]:
            result = ResultFactory(
                event=RankedEventFactory(
                    organizer=league.organizer,
                    category=league.category,
                    format=league.format,
                    date=date,
                )
            )

        results = league.get_results()
        actual_dates = [r.event.date for r in results]
        self.assertEqual(
            actual_dates,
            [
                datetime.date(2024, 7, 1),
                datetime.date(2024, 7, 31),
            ],
        )

    def test_get_results_without_playoffs(self):
        league = OrganizerLeagueFactory(
            playoffs=True,
        )
        event_with_playoffs = RankedEventFactory(
            format=league.format,
            organizer=league.organizer,
            category=league.category,
        )
        for ser in [None, Result.SingleEliminationResult.WINNER]:
            ResultFactory(single_elimination_result=ser, event=event_with_playoffs)

        result_without_playoffs = ResultFactory(
            event=RankedEventFactory(
                format=league.format,
                organizer=league.organizer,
                category=league.category,
            )
        )

        results = league.get_results()
        self.assertEqual(len(results), 3)

        league.playoffs = False
        league.save()
        results = league.get_results()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], result_without_playoffs)
