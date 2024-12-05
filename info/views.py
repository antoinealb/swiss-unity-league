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

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic import TemplateView

from championship.season import ALL_SEASONS_LIST, INVISIBLE_SEASONS, find_season_by_slug


def template_exists(template_name):
    try:
        get_template(template_name)
        return True
    except TemplateDoesNotExist:
        return False


class InformationView(TemplateView):
    def dispatch(self, request, *args, **kwargs):
        path_segments = [segment for segment in request.path.split("/") if segment]
        try:
            season_slug = path_segments[1]
            self.current_season = find_season_by_slug(season_slug)
            path_segments.pop(1)
        except (KeyError, IndexError):
            self.current_season = settings.DEFAULT_SEASON
        self.base_template_name = "_".join(path_segments) + ".html"
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [f"info/{self.current_season.slug}/{self.base_template_name}"]

    def get_view_name(self):
        view_name = self.request.resolver_match.url_name
        if "for_season" not in view_name:
            return view_name + "_for_season"
        return view_name

    def get_seasons_with_template(self):
        return [
            season
            for season in ALL_SEASONS_LIST
            if template_exists(f"info/{season.slug}/{self.base_template_name}")
            and season not in INVISIBLE_SEASONS
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seasons"] = self.get_seasons_with_template()
        context["current_season"] = self.current_season
        context["view_name"] = self.get_view_name()
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
