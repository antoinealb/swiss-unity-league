from django.urls import path, include
from rest_framework import routers
from . import views

api_router = routers.DefaultRouter()
api_router.register(
    r"future-events", views.FutureEventViewSet, basename="future-events"
)
api_router.register(r"past-events", views.PastEventViewSet, basename="past-events")

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("ranking", views.CompleteRankingView.as_view(), name="ranking"),
    path("player/<int:pk>/", views.PlayerDetailsView.as_view(), name="player_details"),
    path("info", views.InformationForPlayerView.as_view(), name="info"),
    path(
        "info/organizer",
        views.InformationForOrganizerView.as_view(),
        name="info_organizer",
    ),
    path("events", views.FutureEventView.as_view(), name="events"),
    path("events/create", views.CreateEventView.as_view(), name="events_create"),
    path("events/<int:pk>/update", views.update_event, name="event_update"),
    path(
        "events/<int:pk>/delete", views.EventDeleteView.as_view(), name="event_delete"
    ),
    path("events/<int:pk>/copy", views.copy_event, name="event_copy"),
    path("events/<int:pk>/", views.EventDetailsView.as_view(), name="event_details"),
    path("results/create", views.CreateResultsView.as_view(), name="results_create"),
    path(
        "results/create/eventlink",
        views.CreateEvenlinkResultsView.as_view(),
        name="results_create_eventlink",
    ),
    path(
        "results/create/aetherhub",
        views.CreateAetherhubResultsView.as_view(),
        name="results_create_aetherhub",
    ),
    path(
        "organizer/edit", views.OrganizerProfileEdit.as_view(), name="organizer_update"
    ),
    path("api/", include(api_router.urls)),
    path("api/formats/", views.ListFormats.as_view(), name="formats-list"),
]
