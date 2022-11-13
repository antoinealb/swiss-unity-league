import datetime
from django.shortcuts import render, get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic import DetailView

from .models import Player, compute_scores, Event, EventPlayerResult
from django.db.models import F

EVENTS_ON_PAGE = 10
PLAYERS_TOP = 10


class IndexView(TemplateView):
    template_name = "championship/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = self._players()
        context["future_events"] = self._future_events()
        return context

    def _players(self):
        players = list(Player.objects.all())
        scores_by_player = compute_scores()
        for p in players:
            p.score = scores_by_player[p.id]
        players.sort(key=lambda l: l.score, reverse=True)
        players = players[:PLAYERS_TOP]
        return players

    def _future_events(self):
        future_events = Event.objects.filter(date__gt=datetime.date.today()).order_by(
            "date"
        )[:EVENTS_ON_PAGE]


class PlayerDetailsView(DetailView):
    template_name = "championship/player_details.html"
    model = Player
    context_object_name = "player"

    def get_context_data(self, object, **kwargs):
        context = super().get_context_data(**kwargs)
        scores = compute_scores()
        context["score"] = scores[object.id]
        context["last_events"] = (
            EventPlayerResult.objects.filter(player=context["player"])
            .annotate(name=F("event__name"), date=F("event__date"))
            .order_by("-event__date")
        )
        return context


class CompleteRankingView(TemplateView):
    template_name = "championship/ranking.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        players = list(Player.objects.all())
        scores_by_player = compute_scores()
        for p in players:
            p.score = scores_by_player[p.id]
        players.sort(key=lambda l: l.score, reverse=True)
        context["players"] = players

        return context


class InformationForPlayerView(TemplateView):
    template_name = "championship/info.html"
