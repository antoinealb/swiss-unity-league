import datetime
import logging
import re
import os
import requests
import random

from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import DeleteView
from django.views.generic import DetailView
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

from rest_framework import viewsets

from .models import *
from .forms import *
from django.db.models import F
from championship import aetherhub_parser
from championship import eventlink_parser
from championship.serializers import EventSerializer

EVENTS_ON_PAGE = 10
PLAYERS_TOP = 10


class IndexView(TemplateView):
    template_name = "championship/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = self._players()
        context["future_events"] = self._future_events()
        context["partner_logos"] = self._partner_logos()
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

    def _partner_logos(self):
        paths = [s / "partner_logos" for s in settings.STATICFILES_DIRS]
        images = sum([os.listdir(p) for p in paths], start=[])
        images = [os.path.join("partner_logos", i) for i in images]

        # Just make sure we don't always have the pictures in the same order
        # to be fair to everyone
        random.shuffle(images)
        return images


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


class InformationForOrganizerView(TemplateView):
    template_name = "championship/info_organizer.html"


@login_required
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


@login_required
def update_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if event.organizer.user != request.user:
        return HttpResponseForbidden()

    if request.method == "POST":
        form = EventCreateForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Succesfully saved event")
            return HttpResponseRedirect(reverse("event_details", args=[event.id]))
    else:
        form = EventCreateForm(instance=event)

    return render(
        request, "championship/update_event.html", {"form": form, "event": event}
    )


class EventDeleteView(DeleteView, LoginRequiredMixin):
    model = Event
    success_url = reverse_lazy("events")

    def get_queryset(self):
        qs = super(EventDeleteView, self).get_queryset()
        return qs.filter(organizer__user=self.request.user)


@login_required
def create_results_eventlink(request):

    form = EventlinkImporterForm(request.user)

    if request.method == "POST":
        form = EventlinkImporterForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            # From here we can assume that the event exists and is owned by
            # this user, as otherwise the form validation will not accept it.
            event = form.cleaned_data["event"]
            text = "".join(s.decode() for s in request.FILES["standings"].chunks())

            try:
                results = eventlink_parser.parse_standings_page(text)
            except:
                messages.error(
                    request,
                    "Error: Could not parse standings file. Did you upload the HTML standings correctly?",
                )
                return render(
                    request,
                    "championship/create_results.html",
                    {"form": form},
                    status=400,
                )

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


@login_required
def create_results_aetherhub(request):
    if request.method == "POST":
        form = AetherhubImporterForm(request.user, request.POST)
        if form.is_valid():
            # From here we can assume that the event exists and is owned by
            # this user, as otherwise the form validation will not accept it.
            url = form.cleaned_data["url"]
            event = form.cleaned_data["event"]

            # Fetch results from Aetherhub and parse them
            try:
                response = requests.get(url)
                response.raise_for_status()
                results = aetherhub_parser.parse_standings_page(
                    response.content.decode()
                )
            except:
                # If anything went wrong with the request, just return to the
                # form.
                messages.error(
                    request, "Could not fetch standings information from Aetherhub."
                )
                return render(
                    request,
                    "championship/create_results.html",
                    {"form": form},
                    status=500,
                )

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


@login_required
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


class FutureEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """

    queryset = Event.objects.filter(date__gte=datetime.date.today()).order_by("date")
    serializer_class = EventSerializer


class FutureEventView(TemplateView):
    template_name = "championship/future_events.html"
