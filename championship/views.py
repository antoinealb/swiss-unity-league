from django.shortcuts import render
from .models import Player, compute_scores


def index(request):
    players = list(Player.objects.all())
    scores_by_player = compute_scores()
    for p in players:
        p.score = scores_by_player[p.id]
    players.sort(key=lambda l: l.score, reverse=True)
    return render(request, "championship/index.html", dict(players=players))
