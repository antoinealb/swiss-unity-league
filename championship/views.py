import datetime
from django.shortcuts import render, get_object_or_404
from django.views.generic.base import TemplateView
from .models import Player, compute_scores, Event, EventPlayerResult
from django.db.models import F

EVENTS_ON_PAGE = 10
PLAYERS_TOP = 10


def index(request):
    players = list(Player.objects.all())
    scores_by_player = compute_scores()
    for p in players:
        p.score = scores_by_player[p.id]
    players.sort(key=lambda l: l.score, reverse=True)
    players = players[:PLAYERS_TOP]

    last_events = Event.objects.filter(date__lte=datetime.date.today()).order_by(
        "-date"
    )[:EVENTS_ON_PAGE]

    future_events = Event.objects.filter(date__gt=datetime.date.today()).order_by(
        "date"
    )[:EVENTS_ON_PAGE]

    return render(
        request,
        "championship/index.html",
        dict(players=players, last_events=last_events, future_events=future_events),
    )


def player_details(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    scores = compute_scores()
    player.score = scores[player.id]
    last_events = (
        EventPlayerResult.objects.filter(player=player)
        .annotate(name=F("event__name"), date=F("event__date"))
        .order_by("-event__date")
    )
    return render(
        request,
        "championship/player_details.html",
        dict(player=player, last_events=last_events),
    )


def ranking(request):
    players = list(Player.objects.all())
    scores_by_player = compute_scores()
    for p in players:
        p.score = scores_by_player[p.id]
    players.sort(key=lambda l: l.score, reverse=True)

    return render(request, "championship/ranking.html", dict(players=players))


class InformationForPlayerView(TemplateView):
    template_name = "championship/info.html"
