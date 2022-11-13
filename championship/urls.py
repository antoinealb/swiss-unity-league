from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("ranking", views.ranking, name="ranking"),
    path("player/<int:player_id>/", views.player_details, name="player_details"),
    path("info", views.InformationForPlayerView.as_view(), name="info"),
]
