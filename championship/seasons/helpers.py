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

from django.contrib.sites.models import Site

from championship.seasons.definitions import ALL_SEASONS, Season


def seasons_for_site(seasons) -> list[Season]:
    domain = Site.objects.get_current().domain
    return sorted([season for season in seasons if season.domain == domain])


def get_all_seasons() -> list[Season]:
    return seasons_for_site(ALL_SEASONS)


def get_main_seasons() -> list[Season]:
    return [season for season in get_all_seasons() if season.main_season]


def get_default_season() -> Season:
    return [season for season in get_all_seasons() if season.default][0]


def get_seasons_with_scores() -> list[Season]:
    from championship.score.generic import SCOREMETHOD_PER_SEASON

    return seasons_for_site(list(SCOREMETHOD_PER_SEASON.keys()))


def find_season_by_slug(slug: str) -> Season:
    for s in get_all_seasons():
        if s.slug == slug:
            return s
    raise KeyError(f"Unknown season slug '{slug}'")


def find_main_season_by_date(date: datetime.date) -> Season | None:
    for season in get_main_seasons():
        if season.start_date <= date <= season.end_date:
            return season
    return None
