from django.urls import path, include
from rest_framework import routers
from championship.importers import IMPORTER_LIST
from . import views


api_router = routers.DefaultRouter()
api_router.register(
    r"future-events", views.FutureEventViewSet, basename="future-events"
)
api_router.register(r"past-events", views.PastEventViewSet, basename="past-events")

urlpatterns = [
    path(parser.to_url(), parser.view, name=parser.view_name)
    for parser in IMPORTER_LIST
] + [
    path("", views.IndexView.as_view(), name="index"),
    path("ranking", views.CompleteRankingView.as_view(), name="ranking"),
    path("player/<int:pk>/", views.PlayerDetailsView.as_view(), name="player_details"),
    path("info", views.InformationForPlayerView.as_view(), name="info"),
    path(
        "info/<int:season_id>/",
        views.InformationForPlayerView.as_view(),
        name="info_for_season",
    ),
    path(
        "info/organizer",
        views.InformationForOrganizerView.as_view(),
        name="info_organizer",
    ),
    path(
        "info/organizer/<int:season_id>",
        views.InformationForOrganizerView.as_view(),
        name="info_organizer_for_season",
    ),
    path("events", views.FutureEventView.as_view(), name="events"),
    path("events/create", views.CreateEventView.as_view(), name="events_create"),
    path("events/<int:pk>/update", views.update_event, name="event_update"),
    path("events/<int:pk>/delete", views.event_delete, name="event_delete"),
    path("events/<int:pk>/copy", views.copy_event, name="event_copy"),
    path("events/<int:pk>/", views.EventDetailsView.as_view(), name="event_details"),
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
    path("address/<int:pk>/delete/", views.address_delete, name="address_delete"),
    path("api/", include(api_router.urls)),
    path("api/formats/", views.ListFormats.as_view(), name="formats-list"),
]
