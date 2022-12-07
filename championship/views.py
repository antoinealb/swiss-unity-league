import datetime
import logging
import re

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.base import TemplateView
from django.views.generic import DetailView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

import requests

from .models import *
from .forms import *
from django.db.models import F
from championship import aetherhub_parser
from championship import eventlink_parser

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
            p.score = scores_by_player.get(p.id, 0)
        players.sort(key=lambda l: l.score, reverse=True)
        players = players[:PLAYERS_TOP]
        return players

    def _future_events(self):
        future_events = Event.objects.filter(date__gt=datetime.date.today()).order_by(
            "date"
        )[:EVENTS_ON_PAGE]
        return future_events


class PlayerDetailsView(DetailView):
    template_name = "championship/player_details.html"
    model = Player
    context_object_name = "player"

    def get_context_data(self, object, **kwargs):
        context = super().get_context_data(**kwargs)
        scores = compute_scores()
        context["score"] = scores.get(object.id, 0)
        context["last_events"] = (
            EventPlayerResult.objects.filter(player=context["player"])
            .annotate(
                name=F("event__name"),
                date=F("event__date"),
                category=F("event__category"),
            )
            .order_by("-event__date")
        )
        for e in context["last_events"]:
            e.qps = qps_for_result(e, e.category)
        return context


class EventDetailsView(DetailView):
    template_name = "championship/event_details.html"
    model = Event
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        results = (
            EventPlayerResult.objects.filter(event=context["event"])
            .annotate(player_name=F("player__name"), category=F("event__category"))
            .order_by("-points")
        )

        for r in results:
            r.qps = qps_for_result(r, r.category)
        context["results"] = results

        return context


class CompleteRankingView(TemplateView):
    template_name = "championship/ranking.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        players = list(Player.objects.all())
        scores_by_player = compute_scores()
        for p in players:
            p.score = scores_by_player.get(p.id, 0)
        players.sort(key=lambda l: l.score, reverse=True)
        context["players"] = players

        return context


class InformationForPlayerView(TemplateView):
    template_name = "championship/info.html"


def create_event(request):
    if request.method == "POST":
        form = EventCreateForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = EventOrganizer.objects.get(user=request.user)
            event.save()

            messages.success(request, "Succesfully created event!")

            return HttpResponseRedirect(reverse("event_details", args=[event.id]))
    else:
        form = EventCreateForm()

    return render(request, "championship/create_event.html", {"form": form})


def create_results_eventlink(request):

    form = EventlinkImporterForm(request.user)

    if request.method == "POST":
        form = EventlinkImporterForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            # From here we can assume that the event exists and is owned by
            # this user, as otherwise the form validation will not accept it.
            event = form.cleaned_data["event"]
            text = "".join(s.decode() for s in request.FILES["standings"].chunks())
            results = eventlink_parser.parse_standings_page(text)

            for (
                name,
                points,
            ) in results:
                player, _ = Player.objects.get_or_create(name=name)
                EventPlayerResult.objects.create(
                    points=points, player=player, event=event
                )

            return HttpResponseRedirect("/")

    return render(request, "championship/create_results.html", {"form": form})


def create_results_aetherhub(request):
    if request.method == "POST":
        form = AetherhubImporterForm(request.user, request.POST)
        if form.is_valid():
            # From here we can assume that the event exists and is owned by
            # this user, as otherwise the form validation will not accept it.
            url = form.cleaned_data["url"]
            event = form.cleaned_data["event"]

            # Fetch results from Aetherhub and parse them
            response = requests.get(url)
            response.raise_for_status()
            results = aetherhub_parser.parse_standings_page(response.content.decode())

            # Create reports for this events
            event.round_count = results.round_count
            event.save()

            # TODO: Fetch players from DB if they exist
            # TODO: Fuzzy match player names with DB
            # TODO: Should we delete all results for that tournament before
            # adding them in case someone uploads results twice ?

            def _remove_camel_case(name):
                """Converts "AntoineAlbertelli" to "Antoine Albertelli"."""
                name = "".join(map(lambda c: c if c.islower() else " " + c, name))
                # Normalizes whitespace in case there are double space or tabs
                name = re.sub(r"\s+", " ", name)
                return name.lstrip()

            for name, points, _ in results.standings:
                name = _remove_camel_case(name)

                player, _ = Player.objects.get_or_create(name=name)
                EventPlayerResult.objects.create(
                    points=points, player=player, event=event
                )

            return HttpResponseRedirect("/")
    else:
        form = AetherhubImporterForm(request.user)

    return render(request, "championship/create_results.html", {"form": form})


def create_results(request):
    form = ImporterSelectionForm()

    if request.method == "POST":
        form = ImporterSelectionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["site"] == ImporterSelectionForm.Importers.AETHERHUB:
                return redirect(reverse("results_create_aetherhub"))
            elif form.cleaned_data["site"] == ImporterSelectionForm.Importers.EVENTLINK:
                return redirect(reverse("results_create_eventlink"))

    return render(request, "championship/create_results.html", {"form": form})
