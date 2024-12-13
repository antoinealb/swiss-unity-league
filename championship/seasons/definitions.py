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
import functools
from dataclasses import dataclass
from typing import Any

from multisite.constants import GLOBAL_DOMAIN, SWISS_DOMAIN


@dataclass(frozen=True)
@functools.total_ordering
class Season:
    name: str
    slug: str
    start_date: datetime.date
    end_date: datetime.date
    result_deadline: datetime.timedelta = datetime.timedelta(days=7)
    domain: str = SWISS_DOMAIN
    # Whether it's a main (yearly) season and not a special one
    main_season: bool = False
    # Whether this is the default season to show on the website
    default: bool = False
    # Whether the season is shown in the dropdown
    visible: bool = True

    def can_enter_results(self, on_date: datetime.date) -> bool:
        """Checks if results can still be added to this season on a given date."""
        return on_date <= self.end_date + self.result_deadline

    def __lt__(self, other: "Season") -> bool:
        if self.start_date != other.start_date:
            return self.start_date > other.start_date
        return self.end_date < other.end_date

    def __eq__(self, other: Any) -> bool:
        return (self.start_date, self.end_date) == (other.start_date, other.end_date)


SEASON_2023 = Season(
    start_date=datetime.date(2023, 1, 1),
    end_date=datetime.date(2023, 10, 31),
    name="Season 2023",
    slug="2023",
    main_season=True,
)

SEASON_2024 = Season(
    start_date=datetime.date(2023, 11, 1),
    end_date=datetime.date(2024, 10, 31),
    name="Season 2024",
    slug="2024",
    main_season=True,
)

SEASON_2025 = Season(
    start_date=datetime.date(2024, 11, 1),
    end_date=datetime.date(2025, 10, 31),
    name="Season 2025",
    slug="2025",
    main_season=True,
    default=True,
)

INVITATIONAL_SPRING_2025 = Season(
    start_date=SEASON_2025.start_date,
    end_date=datetime.date(2025, 3, 31),
    name="Spring Invitational 2025",
    slug="invitational-spring-2025",
)

SWISS_SEASONS = [
    SEASON_2025,
    INVITATIONAL_SPRING_2025,
    SEASON_2024,
    SEASON_2023,
]

EU_SEASON_2025 = Season(
    start_date=datetime.date(2025, 1, 1),
    end_date=datetime.date(2025, 9, 30),
    name="Season 2025",
    slug="eu-2025",
    domain=GLOBAL_DOMAIN,
    main_season=True,
    default=True,
)

EU_SEASONS = [EU_SEASON_2025]

SEASON_ALL = Season(
    start_date=min([s.start_date for s in SWISS_SEASONS if s.main_season]),
    end_date=max([s.end_date for s in SWISS_SEASONS if s.main_season]),
    name="all seasons",
    slug="all",
)

ALL_SEASONS = SWISS_SEASONS + EU_SEASONS + [SEASON_ALL]
MAIN_SEASONS = [s for s in ALL_SEASONS if s.main_season]


def assert_single_default(seasons, domain):
    default_count = sum(
        1 for season in seasons if season.domain == domain and season.default
    )
    assert default_count <= 1, f"Multiple default seasons found for {domain} domain."


# Assert that there's only one default season per domain
assert_single_default(ALL_SEASONS, SWISS_DOMAIN)
assert_single_default(ALL_SEASONS, GLOBAL_DOMAIN)