import datetime
import logging
import re
import os
import requests
import random
from typing import *

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
from championship.parsers import aetherhub, eventlink, mtgevent, challonge
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


def _points_from_score(score: str) -> int:
    """Parses the number of points from score

    TODO: More robust parsing required (proper parser?)
    >>> _points_from_score('3-0-1')
    10

    >>> _points_from_score('3-0-0')
    9

    >>> _points_from_score('3-0')
    9
    """
    score = [int(s) for s in score.split("-")]
    return sum(a * b for a, b in zip(score, (3, 0, 1)))


@login_required
def create_results_manual(request):
    formset = ResultsFormset()
    metadata_form = ManualUploadMetadataForm(user=request.user)

    if request.method == "POST":
        formset = ResultsFormset(request.POST)
        metadata_form = ManualUploadMetadataForm(user=request.user, data=request.POST)
        if formset.is_valid() and metadata_form.is_valid():
            event = metadata_form.cleaned_data["event"]
            for ranking, result in enumerate(formset.cleaned_data):
                try:
                    name = result["name"]
                    points = _points_from_score(result["points"])
                except KeyError:
                    continue

                name = re.sub(r"\s+", " ", name)
                try:
                    player = PlayerAlias.objects.get(name=name).true_player
                except PlayerAlias.DoesNotExist:
                    player, _ = Player.objects.get_or_create(name=name)

                EventPlayerResult.objects.create(
                    event=event, player=player, points=points, ranking=ranking + 1
                )

            return HttpResponseRedirect(event.get_absolute_url())

    players = Player.leaderboard_objects.all()
    context = {
        "metadata_form": metadata_form,
        "formset": formset,
        "players": players,
    }
    return render(request, "championship/create_results_manual.html", context=context)


def clean_name(name: str) -> str:
    """Normalizes the given name based on observations from results uploaded.

    This function applies transformations to the provided input so that the
    result is a clean name ready to be put in the DB.

    For example, all of the following inputs map to the normalized "Antoine Albertelli":

        -Camel Case: "AntoineAlbertelli"
        -All Caps: "Antoine ALBERTELLI"
        -Snake case: "Antoine_Albertelli"
        -Multiple (and leading/trailing) white spaces/tabs: "   Antoine    Albertelli   "
        -Lower case: "antoine albertelli"
    """
    name = name.replace("_", " ")
    name = re.sub(
        r"([A-Z])([A-Z]+)", lambda match: match.group(1) + match.group(2).lower(), name
    )
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    # Normalizes whitespace in case there are double space or tabs
    name = re.sub(r"\s+", " ", name)

    return name.strip().title()


class CreateResultsView(FormView):
    """Generic view that handles the logic for importing results.

    This view encapsulate all the code that should be website-independent for
    importing results, such as validating a form, looking for events, etc.

    To use this class, the user simply needs to implement the get_results
    method, which contains all the parsing logic. See
    CreateAetherhubResultsView for an example.
    """

    template_name = "championship/create_results.html"

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        k["user"] = self.request.user
        return k

    def get_results(self, form):
        """This function must be implemented to actually parse results.

        It returns a list of standings, or None if parsing was not succesful.
        """
        raise ImproperlyConfigured("No parser implemented")

    def form_valid(self, form):
        """Processes a succesful result creation form.

        This part of the processing is generic and does not depend on which
        website we use for parsing.
        """
        # From here we can assume that the event exists and is owned by
        # this user, as otherwise the form validation will not accept it.
        self.event = form.cleaned_data["event"]
        standings = self.get_results(form)

        if not standings:
            return render(
                self.request,
                self.template_name,
                {"form": form},
                status=400,
            )

        for i, (name, points) in enumerate(standings):
            name = clean_name(name)
            try:
                player = PlayerAlias.objects.get(name=name).true_player
            except PlayerAlias.DoesNotExist:
                player, _ = Player.objects.get_or_create(name=name)

            EventPlayerResult.objects.create(
                points=points, player=player, event=self.event, ranking=i + 1
            )

        return super().form_valid(form)

    def get_success_url(self):
        return self.event.get_absolute_url()


class CreateLinkParserResultsView(LoginRequiredMixin, CreateResultsView):
    form_class = LinkImporterForm
    parser = None
    help_text = None
    placeholder = None

    def clean_url(self, url):
        raise NotImplementedError("This method has not been implemented yet.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"help_text": self.help_text, "placeholder": self.placeholder})
        return kwargs

    def get_results(self, form):
        url = form.cleaned_data["url"]
        url = self.clean_url(url)

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return self.parser.parse_standings_page(response.content.decode())
        except:
            messages.error(self.request, "Could not fetch standings.")


class CreateHTMLParserResultsView(LoginRequiredMixin, CreateResultsView):
    form_class = HtmlImporterForm
    parser = None

    def get_results(self, form):
        text = "".join(s.decode() for s in self.request.FILES["standings"].chunks())

        try:
            return self.parser.parse_standings_page(text)
        except:
            messages.error(
                self.request,
                "Error: Could not parse standings file. Did you upload the HTML standings correctly?",
            )


class CreateAetherhubResultsView(CreateLinkParserResultsView):
    parser = aetherhub
    help_text = (
        "Link to your tournament. Make sure it is a public and finished tournament."
    )
    placeholder = "https://aetherhub.com/Tourney/RoundTourney/123456"

    def clean_url(self, url):
        """Normalizes the given tournament url to point to the RoundTourney page."""
        url_re = r"https://aetherhub.com/Tourney/[a-zA-Z]+/(\d+)"
        tourney = re.match(url_re, url).group(1)
        return f"https://aetherhub.com/Tourney/RoundTourney/{tourney}"


class CreateChallongeResultsView(CreateLinkParserResultsView):
    parser = challonge
    help_text = (
        "Link to your tournament. Make sure the tournament system is Swiss rounds."
    )
    placeholder = "https://challonge.com/de/rk6vluaa"

    def clean_url(self, url):
        return challonge.clean_url(url)


class CreateEvenlinkResultsView(CreateHTMLParserResultsView):
    parser = eventlink


class CreateMtgEventResultsView(CreateHTMLParserResultsView):
    parser = mtgevent.parse_standings_page


class ChooseUploaderView(LoginRequiredMixin, FormView):
    template_name = "championship/create_results.html"
    form_class = ImporterSelectionForm

    def form_valid(self, form):
        from championship.importers import IMPORTER_LIST

        urls_for_type = {
            parser.name.upper(): reverse(parser.view_name) for parser in IMPORTER_LIST
        }
        return HttpResponseRedirect(urls_for_type[form.cleaned_data["site"]])


class AddTop8ResultsView(LoginRequiredMixin, FormView):
    template_name = "championship/add_top8_results.html"
    form_class = AddTop8ResultsForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["event"] = get_object_or_404(
            Event, pk=self.kwargs["pk"], organizer__user=self.request.user
        )
        return kwargs

    def form_valid(self, form):
        self.event = Event.objects.get(id=self.kwargs["pk"])

        if self.event.category == Event.Category.REGULAR:
            messages.error(self.request, "Top 8 are not allowed at SUL Regular.")
            return super().form_valid(form)

        FIELDS_TO_RESULTS = {
            "winner": EventPlayerResult.SingleEliminationResult.WINNER,
            "finalist": EventPlayerResult.SingleEliminationResult.FINALIST,
            "semi0": EventPlayerResult.SingleEliminationResult.SEMI_FINALIST,
            "semi1": EventPlayerResult.SingleEliminationResult.SEMI_FINALIST,
            "quarter0": EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
            "quarter1": EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
            "quarter2": EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
            "quarter3": EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
        }

        self.event.eventplayerresult_set.update(single_elimination_result=None)
        for key, result in FIELDS_TO_RESULTS.items():
            w = form.cleaned_data[key]

            if w is None:
                continue

            w.single_elimination_result = result
            w.save()

        return super().form_valid(form)

    def get_success_url(self):
        return self.event.get_absolute_url()


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
