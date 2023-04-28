import datetime
import logging
import re
import os
import requests
import random

from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import DeleteView, FormView, UpdateView
from django.views.generic import DetailView
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

from rest_framework import viewsets, views
from rest_framework.response import Response

from .models import *
from .forms import *
from django.db.models import F, Q
from championship import aetherhub_parser
from championship import eventlink_parser
from championship import mtgevent_parser
from championship.serializers import EventSerializer
from .parsers import PARSER_LIST

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
        players = list(Player.leaderboard_objects.all())
        scores_by_player = compute_scores()
        for p in players:
            p.score = scores_by_player.get(p.id, 0)
        players.sort(key=lambda l: l.score, reverse=True)
        players = players[:PLAYERS_TOP]
        return players

    def _future_events(self):
        future_events = (
            Event.objects.filter(date__gt=datetime.date.today())
            .exclude(category=Event.Category.REGULAR)
            .order_by("date")[:EVENTS_ON_PAGE]
            .select_related("organizer")
        )
        return future_events

    def _partner_logos(self):
        paths = [s / "partner_logos" for s in settings.STATICFILES_DIRS]
        images = sum([os.listdir(p) for p in paths], start=[])
        images = ["partner_logos/" + i for i in images if i.endswith("png")]

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
                event_size=Count("event__eventplayerresult"),
                top8_cnt=Count(
                    "event__eventplayerresult",
                    filter=Q(event__eventplayerresult__single_elimination_result__gt=0),
                ),
            )
            .order_by("-event__date")
        )
        for e in context["last_events"]:
            has_top8 = e.top8_cnt > 0
            e.qps = qps_for_result(
                e,
                e.category,
                event_size=e.event_size,
                has_top_8=has_top8,
            )
        return context


class EventDetailsView(DetailView):
    template_name = "championship/event_details.html"
    model = Event
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        results = EventPlayerResult.objects.filter(event=context["event"]).annotate(
            player_name=F("player__name"),
            category=F("event__category"),
            event_size=Count("event__eventplayerresult"),
            top8_cnt=Count(
                "event__eventplayerresult",
                filter=Q(event__eventplayerresult__single_elimination_result__gt=0),
            ),
        )

        for r in results:
            has_top8 = r.top8_cnt > 0
            r.qps = qps_for_result(
                r, r.category, event_size=r.event_size, has_top_8=has_top8
            )

        results = sorted(results)

        top_results = []

        while results and results[0].single_elimination_result:
            top_results.append(results.pop(0))

        context["results"] = results
        context["top_results"] = top_results

        return context


class CompleteRankingView(TemplateView):
    template_name = "championship/ranking.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        players = list(Player.leaderboard_objects.all())
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


class CreateEventView(LoginRequiredMixin, FormView):
    template_name = "championship/create_event.html"
    form_class = EventCreateForm

    def form_valid(self, form):
        event = form.save(commit=False)
        event.organizer = EventOrganizer.objects.get(user=self.request.user)
        event.save()

        messages.success(self.request, "Succesfully created event!")

        return HttpResponseRedirect(reverse("event_details", args=[event.id]))


@login_required
def copy_event(request, pk):
    original_event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        form = EventCreateForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.pk = None  # Force django to commit
            event.organizer = EventOrganizer.objects.get(user=request.user)
            event.save()

            messages.success(request, "Succesfully created event!")

            return HttpResponseRedirect(reverse("event_details", args=[event.id]))
    else:
        # By default, copy it one week later
        new_event = get_object_or_404(Event, pk=pk)
        new_event.date += datetime.timedelta(days=7)
        form = EventCreateForm(instance=new_event)

    return render(
        request,
        "championship/copy_event.html",
        {"form": form, "original_event": original_event},
    )


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


class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    success_url = reverse_lazy("events")

    def get_queryset(self):
        qs = super(EventDeleteView, self).get_queryset()
        return qs.filter(organizer__user=self.request.user)


class CreateResultsView(FormView):
    """Generic view that handles the logic for importing results.

    This view encapsulate all the code that should be website-independent for
    importing results, such as validating a form, looking for events, etc.

    To use this class, the user simply needs to implement the get_results
    method, which contains all the parsing logic. See
    CreateAetherhubResultsView for an example.
    """

    template_name = "championship/create_results.html"
    success_url = "/"

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        k["user"] = self.request.user
        return k

    def get_results(self, form):
        """This function must be implemented to actually parse results.

        It returns a list of standings, or None if parsing was not succesful.
        """
        raise ImproperlyConfigured("No parser implemented")

    def _remove_camel_case(self, name):
        """Converts "AntoineAlbertelli" to "Antoine Albertelli"."""
        name = "".join(map(lambda c: c if c.islower() else " " + c, name))
        # Normalizes whitespace in case there are double space or tabs
        name = re.sub(r"\s+", " ", name)
        return name.lstrip()

    def form_valid(self, form):
        """Processes a succesful result creation form.

        This part of the processing is generic and does not depend on which
        website we use for parsing.
        """
        # From here we can assume that the event exists and is owned by
        # this user, as otherwise the form validation will not accept it.
        event = form.cleaned_data["event"]
        standings = self.get_results(form)

        if not standings:
            return render(
                self.request,
                self.template_name,
                {"form": form},
                status=400,
            )

        for i, (name, points) in enumerate(standings):
            name = self._remove_camel_case(name)
            try:
                player = PlayerAlias.objects.get(name=name).true_player
            except PlayerAlias.DoesNotExist:
                player, _ = Player.objects.get_or_create(name=name)

            EventPlayerResult.objects.create(
                points=points, player=player, event=event, ranking=i + 1
            )

        return super().form_valid(form)


class CreateAetherhubResultsView(LoginRequiredMixin, CreateResultsView):
    form_class = AetherhubImporterForm

    def clean_aetherhub_url(self, url):
        """Normalizes the given tournament url to point to the RoundTourney page."""
        url_re = r"https://aetherhub.com/Tourney/[a-zA-Z]+/(\d+)"
        tourney = re.match(url_re, url).group(1)
        return f"https://aetherhub.com/Tourney/RoundTourney/{tourney}"

    def get_results(self, form):
        url = form.cleaned_data["url"]
        url = self.clean_aetherhub_url(url)

        # Fetch results from Aetherhub and parse them
        try:
            response = requests.get(url)
            response.raise_for_status()
            results = aetherhub_parser.parse_standings_page(response.content.decode())
            return results.standings
        except:
            # If anything went wrong with the request, just return to the
            # form.
            messages.error(
                self.request, "Could not fetch standings information from Aetherhub."
            )


class CreateEvenlinkResultsView(LoginRequiredMixin, CreateResultsView):
    form_class = HtmlImporterForm

    def get_results(self, form):
        text = "".join(s.decode() for s in self.request.FILES["standings"].chunks())

        try:
            return eventlink_parser.parse_standings_page(text)
        except:
            messages.error(
                self.request,
                "Error: Could not parse standings file. Did you upload the HTML standings correctly?",
            )


class CreateMtgEventResultsView(LoginRequiredMixin, CreateResultsView):
    form_class = HtmlImporterForm

    def get_results(self, form):
        text = "".join(s.decode() for s in self.request.FILES["standings"].chunks())

        try:
            return mtgevent_parser.parse_standings_page(text)
        except:
            messages.error(
                self.request,
                "Error: Could not parse standings file. Did you upload the HTML standings correctly?",
            )


class CreateResultsView(LoginRequiredMixin, FormView):
    template_name = "championship/create_results.html"
    form_class = ImporterSelectionForm

    def form_valid(self, form):
        urls_for_type = {
            parser.name.upper(): parser.to_url(True) for parser in PARSER_LIST
        }
        return HttpResponseRedirect(urls_for_type[form.cleaned_data["site"]])


class FutureEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """

    serializer_class = EventSerializer

    def get_queryset(self):
        """Returns all Events in the future."""

        # This needs to be a function (get_queryset) instead of an attribute as
        # otherwise the today means "when the app was started.
        qs = Event.objects.filter(date__gte=datetime.date.today())
        qs = qs.select_related("organizer")
        return qs.order_by("date")


class PastEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """

    serializer_class = EventSerializer

    def get_queryset(self):
        """Returns all Events in the past."""

        # This needs to be a function (get_queryset) instead of an attribute as
        # otherwise the today means "when the app was started.
        qs = Event.objects.filter(date__lt=datetime.date.today())
        return qs.order_by("-date")


class ListFormats(views.APIView):
    """View to list all Magic formats we play for the league."""

    def get(self, request, format=None):
        return Response(sorted(Event.Format.labels))


class FutureEventView(TemplateView):
    template_name = "championship/future_events.html"


class OrganizerProfileEdit(LoginRequiredMixin, UpdateView):
    model = EventOrganizer
    fields = ["name", "contact"]
    template_name = "championship/update_organizer.html"
    success_url = reverse_lazy("organizer_update")

    def get_object(self):
        return EventOrganizer.objects.get(user=self.request.user)
