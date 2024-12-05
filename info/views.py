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

from django.urls import reverse
from django.views.generic import TemplateView

from championship.season import SEASONS_WITH_INFO
from championship.views.base import PerSeasonMixin


class InformationForPlayerView(PerSeasonMixin, TemplateView):
    template_path = "info/{slug}/info_player.html"
    season_view_name = "info_for_season"
    season_list = SEASONS_WITH_INFO


class InformationForOrganizerView(PerSeasonMixin, TemplateView):
    template_path = "info/{slug}/info_organizer.html"
    season_view_name = "info_organizer_for_season"
    season_list = SEASONS_WITH_INFO


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
