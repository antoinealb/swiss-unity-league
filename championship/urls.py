from django.urls import path
from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("ranking", views.CompleteRankingView.as_view(), name="ranking"),
    path("player/<int:pk>/", views.PlayerDetailsView.as_view(), name="player_details"),
    path("info", views.InformationForPlayerView.as_view(), name="info"),
    path("events/create", views.create_event, name="events_create"),
    path("results/create", views.create_results, name="results_create"),
    path(
        "results/create/eventlink",
        views.create_results_eventlink,
        name="results_create_eventlink",
    ),
    path(
        "results/create/aetherhub",
        views.create_results_aetherhub,
        name="results_create_aetherhub",
    ),
]
