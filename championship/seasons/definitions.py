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
import re
from dataclasses import dataclass
from typing import Any

from django.core.checks import Error, register

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
    slug="spring2025invitational",
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
    slug="eu2025",
    domain=GLOBAL_DOMAIN,
    main_season=True,
)

# Introduce a mockup season to test the leaderboard for eu
EU_SEASON_2024_MOCKUP = Season(
    start_date=datetime.date(2024, 1, 1),
    end_date=datetime.date(2024, 12, 31),
    name="Mockup Season 2024",
    slug="eu2024mockup",
    domain=GLOBAL_DOMAIN,
    main_season=True,
    default=True,
)

EU_SEASONS = [EU_SEASON_2025, EU_SEASON_2024_MOCKUP]

SEASON_ALL = Season(
    start_date=min([s.start_date for s in SWISS_SEASONS if s.main_season]),
    end_date=max([s.end_date for s in SWISS_SEASONS if s.main_season]),
    name="all seasons",
    slug="all",
)
ALL_SEASONS = SWISS_SEASONS + EU_SEASONS + [SEASON_ALL]
MAIN_SEASONS = [s for s in ALL_SEASONS if s.main_season]


@register()
def check_season_slug_is_compatible(app_configs, **kwargs):
    """
    Checks that season slugs are in a format compatible with DRF API router.
    """
    errors = []
    valid = re.compile(r"^[a-zA-Z0-9]+$")
    for season in ALL_SEASONS:
        if not valid.match(season.slug):
            errors.append(
                Error(
                    "Invalid season slug (must be a-z0-9).",
                    obj=season,
                    id="championship.E001",
                )
            )
    return errors


@register()
def check_default_season_is_unique(app_configs, **kwargs):
    """
    Checks that each domain has one and exactly one default season.
    """
    from django.contrib.sites.models import Site

    errors = []

    for site in Site.objects.all():
        default_seasons = [
            s for s in ALL_SEASONS if s.domain == site.domain and s.default
        ]
        if len(default_seasons) > 1:
            all_slugs = ",".join(s.slug for s in default_seasons)
            errors.append(
                Error(
                    "More than one default season.",
                    hint=f"Default seasons are: {all_slugs}",
                    obj=site,
                    id="championship.E002",
                )
            )
        elif not default_seasons:
            errors.append(
                Error(
                    "No default season for domain",
                    obj=site,
                    id="championship.E003",
                )
            )

    return errors
