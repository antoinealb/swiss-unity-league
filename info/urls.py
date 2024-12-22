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

from django.urls import path
from django.views.generic import RedirectView

from . import views

TEMPLATE_BASE = "info.html"
TEMPLATE_ORGANIZER = "info_organizer.html"
TEMPLATE_PLAYER = "info_player.html"

urlpatterns = [
    path(
        "",
        views.InformationView.as_view(base_template_name=TEMPLATE_BASE),
        name="info",
    ),
    path(
        "<slug:slug>/",
        views.InformationView.as_view(base_template_name=TEMPLATE_BASE),
        name="info_for_season",
    ),
    path(
        "player",
        views.InformationView.as_view(base_template_name=TEMPLATE_PLAYER),
        name="info_player",
    ),
    path(
        "<slug:slug>/player",
        views.InformationView.as_view(base_template_name=TEMPLATE_PLAYER),
        name="info_player_for_season",
    ),
    path(
        "organizer",
        views.InformationView.as_view(base_template_name=TEMPLATE_ORGANIZER),
        name="info_organizer",
    ),
    path(
        "<slug:slug>/organizer",
        views.InformationView.as_view(base_template_name=TEMPLATE_ORGANIZER),
        name="info_organizer_for_season",
    ),
    path(
        "organizer/<slug:slug>",
        RedirectView.as_view(pattern_name="info_organizer_for_season", permanent=True),
    ),
    path("calendar-integration", views.IcalInformationView.as_view(), name="info_ical"),
]
