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

from django.urls import include, path

from championship import ical_feeds
from championship.importers import IMPORTER_LIST

from . import views

urlpatterns = [
    path(parser.to_url(), parser.view, name=parser.view_name)
    for parser in IMPORTER_LIST
] + [
    # Add a temporary url so we can test the challonge link parser again in a few months
    path(
        "results/create/challongelink",
        views.ChallongeLinkResultsView.as_view(),
        name="challonge_create_link_results",
    ),
    path("", views.IndexView.as_view(), name="index"),
    path("ranking", views.CompleteRankingView.as_view(), name="ranking"),
    path(
        "ranking/<slug:slug>",
        views.CompleteRankingView.as_view(),
        name="ranking-by-season",
    ),
    path("player/<int:pk>/", views.PlayerDetailsView.as_view(), name="player_details"),
    path(
        "player/<int:pk>/season/<slug:slug>",
        views.PlayerDetailsView.as_view(),
        name="player_details_by_season",
    ),
    path("info", views.InformationForPlayerView.as_view(), name="info"),
    path(
        "info/<slug:slug>/",
        views.InformationForPlayerView.as_view(),
        name="info_for_season",
    ),
    path(
        "info/organizer",
        views.InformationForOrganizerView.as_view(),
        name="info_organizer",
    ),
    path(
        "info/organizer/<slug:slug>",
        views.InformationForOrganizerView.as_view(),
        name="info_organizer_for_season",
    ),
    path("events", views.FutureEventView.as_view(), name="events"),
    path("events/create", views.CreateEventView.as_view(), name="events_create"),
    path(
        "events/<int:pk>/update", views.EventUpdateView.as_view(), name="event_update"
    ),
    path(
        "events/<int:pk>/delete", views.EventDeleteView.as_view(), name="event_delete"
    ),
    path("events/<int:pk>/copy", views.CopyEventView.as_view(), name="event_copy"),
    path("events/<int:pk>/", views.EventDetailsView.as_view(), name="event_details"),
    path(
        "epr/edit/<int:pk>/",
        views.ResultUpdateView.as_view(),
        name="epr_edit",
    ),
    path("results/create", views.ChooseUploaderView.as_view(), name="results_create"),
    path(
        "results/<int:pk>/top8",
        views.AddTop8ResultsView.as_view(),
        name="results_top8_add",
    ),
    path(
        "results/<int:pk>/delete",
        views.ClearEventResultsView.as_view(),
        name="event_clear_results",
    ),
    path(
        "results/single/<int:pk>/delete/",
        views.SingleResultDeleteView.as_view(),
        name="single_result_delete",
    ),
    path("organizer/", views.OrganizerListView.as_view(), name="organizer_view"),
    path(
        "organizer/<int:pk>",
        views.EventOrganizerDetailView.as_view(),
        name="organizer_details",
    ),
    path(
        "organizer/edit",
        views.OrganizerProfileEditView.as_view(),
        name="organizer_update",
    ),
    path("address/", views.AddressListView.as_view(), name="address_list"),
    path("address/create/", views.AddressCreateView.as_view(), name="address_create"),
    path(
        "address/<int:pk>/edit/", views.AddressUpdateView.as_view(), name="address_edit"
    ),
    path(
        "address/<pk>/delete/", views.AddressDeleteView.as_view(), name="address_delete"
    ),
    path("events.ics", ical_feeds.LargeEventFeed(), name="events_feed"),
    path("allevents.ics", ical_feeds.AllEventsFeed(), name="all_events_feed"),
    path(
        "premierevents.ics", ical_feeds.PremierEventsFeed(), name="premier_events_feed"
    ),
    path("calendar-integration", views.IcalInformationView.as_view(), name="info_ical"),
    path("robots.txt", views.RobotsTxtView.as_view()),
]
