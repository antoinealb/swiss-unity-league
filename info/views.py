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

import os.path
from dataclasses import asdict
from functools import lru_cache

from django.contrib.sites.models import Site
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic import TemplateView

from championship.seasons.helpers import (
    find_season_by_slug,
    get_all_seasons,
    get_default_season,
)


@lru_cache
def template_exists(template_name):
    try:
        get_template(template_name)
        return True
    except TemplateDoesNotExist:
        return False


class InformationView(TemplateView):
    base_template_name = None

    def get_season(self):
        try:
            season = find_season_by_slug(self.kwargs["slug"])
        except KeyError:
            season = get_default_season()
        return season

    def get_template_for_season(self, season):
        return os.path.join(
            "info",
            Site.objects.get_current().domain,
            season.slug,
            self.base_template_name,
        )

    def get_template_names(self):
        return [self.get_template_for_season(self.get_season())]

    def get_seasons_with_template(self):
        return [
            season
            for season in get_all_seasons()
            if season.visible and template_exists(self.get_template_for_season(season))
        ]

    def get_url_for_season(self, season):
        view_name = self.request.resolver_match.url_name
        if "for_season" not in view_name:
            view_name += "_for_season"
        return reverse(view_name, kwargs={"slug": season.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seasons"] = [
            {**asdict(season), "url": self.get_url_for_season(season)}
            for season in self.get_seasons_with_template()
        ]
        context["current_season"] = self.get_season()
        return context


class IcalInformationView(TemplateView):
    template_name = "info/ical.html"

    def events_url(self, view_name: str) -> str:
        return self.request.build_absolute_uri(reverse(view_name))

    def get_context_data(self):
        return {
            "premier_events_url": self.events_url("premier_events_feed"),
            "regional_events_url": self.events_url("events_feed"),
            "all_events_url": self.events_url("all_events_feed"),
        }
