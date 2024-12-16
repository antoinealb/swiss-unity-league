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

import re

from django.core.checks import Error, register

from championship.seasons.definitions import ALL_SEASONS


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
    errors = []

    domains = set(s.domain for s in ALL_SEASONS)

    for domain in domains:
        default_seasons = [s for s in ALL_SEASONS if s.domain == domain and s.default]
        if len(default_seasons) > 1:
            all_slugs = ",".join(s.slug for s in default_seasons)
            errors.append(
                Error(
                    "More than one default season.",
                    hint=f"Default seasons are: {all_slugs}",
                    obj=domain,
                    id="championship.E002",
                )
            )
        elif not default_seasons:
            errors.append(
                Error(
                    "No default season for domain",
                    obj=domain,
                    id="championship.E003",
                )
            )

    return errors
