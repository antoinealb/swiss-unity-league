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
from dataclasses import dataclass


@dataclass(frozen=True)
class Season:
    name: str
    slug: str
    start_date: datetime.date
    end_date: datetime.date
    result_deadline: datetime.timedelta = datetime.timedelta(days=7)

    def can_enter_results(self, on_date: datetime.date) -> bool:
        """Checks if results can still be added to this season on a given date."""
        return on_date <= self.end_date + self.result_deadline


SEASON_2023 = Season(
    start_date=datetime.date(2023, 1, 1),
    end_date=datetime.date(2023, 10, 31),
    name="Season 2023",
    slug="2023",
)

SEASON_2024 = Season(
    start_date=datetime.date(2023, 11, 1),
    end_date=datetime.date(2024, 10, 31),
    name="Season 2024",
    slug="2024",
)

SEASON_2025 = Season(
    start_date=datetime.date(2024, 11, 1),
    end_date=datetime.date(2025, 10, 31),
    name="Season 2025",
    slug="2025",
)

SUL_TRIAL_2024 = Season(
    start_date=SEASON_2024.start_date,
    end_date=datetime.date(2024, 4, 30),
    name="SUL Trial 2024",
    slug="sul-trial-2024",
)

INVITATIONAL_SPRING_2025 = Season(
    start_date=SEASON_2025.start_date,
    end_date=datetime.date(2025, 3, 31),
    name="Invitational Spring 2025",
    slug="invitational-spring-2025",
)

SEASON_LIST = [SEASON_2024, SEASON_2023]

SEASON_AND_TRIAL_LIST = [SEASON_2024, SUL_TRIAL_2024, SEASON_2023]

SEASON_ALL = Season(
    start_date=min([s.start_date for s in SEASON_LIST]),
    end_date=max([s.end_date for s in SEASON_LIST]),
    name="all seasons",
    slug="all",
)

INVISIBLE_SEASONS = [SEASON_2025, INVITATIONAL_SPRING_2025]  # type: ignore
ALL_SEASONS_LIST = SEASON_AND_TRIAL_LIST + [SEASON_ALL]

SEASONS_WITH_INFO = SEASON_LIST
SEASONS_WITH_RANKING = ALL_SEASONS_LIST


def find_season_by_slug(slug: str) -> Season:
    for s in ALL_SEASONS_LIST + INVISIBLE_SEASONS:
        if s.slug == slug:
            return s
    raise KeyError(f"Unknown season slug '{slug}'")


def find_season_by_date(date: datetime.date) -> Season | None:
    for season in SEASON_LIST + INVISIBLE_SEASONS:
        if season.start_date <= date <= season.end_date:
            return season
    return None
