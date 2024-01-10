import csv
import datetime
import re
import logging
import os
from typing import Any
from zipfile import BadZipFile
import requests
import random
import pandas as pd
import io
from typing import *
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from django.views.generic.edit import DeleteView, FormView, UpdateView, CreateView
from django.views.generic import DetailView
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseForbidden,
    Http404,
)
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from rest_framework import viewsets, views
from rest_framework.response import Response
from championship.score import get_results_with_qps, get_leaderboard
from championship.season import (
    SEASON_LIST,
    SEASONS_WITH_INFO,
    SEASONS_WITH_RANKING,
    find_season_by_slug,
)

from championship.parsers.parse_result import ParseResult

from .models import *
from invoicing.models import Invoice
from .forms import *
from championship.parsers import (
    aetherhub,
    eventlink,
    excel_csv_parser,
    mtgevent,
    challonge,
    melee,
)
from championship.parsers.general_parser_functions import record_to_points, parse_record
from championship.serializers import EventSerializer, PlayerAutocompleteSerializer
from championship.tournament_valid import (
    validate_standings,
    get_max_round_error_message,
    TooManyPointsForPlayerError,
    TooManyPointsInTotalError,
    TooManyPointsForTop8Error,
    TooFewPlayersForPremierError,
)
from django.http import JsonResponse
from django.shortcuts import render


class CustomDeleteView(LoginRequiredMixin, DeleteView):
    success_message = "Successfully deleted {verbose_name}!"
    error_message = "You are not allowed to delete this {verbose_name}!"

    def allowed_to_delete(self, object, request):
        return True

    def form_valid(self, form):
        request = self.request
        verbose_name = self.object._meta.verbose_name.lower()
        if self.allowed_to_delete(self.object, request):
            messages.success(
                request, self.success_message.format(verbose_name=verbose_name)
            )
            self.delete(self.request)
        else:
            messages.error(
                request, self.error_message.format(verbose_name=verbose_name)
            )
        return HttpResponseRedirect(self.get_success_url())


EVENTS_ON_PAGE = 10
PLAYERS_TOP = 10


class IndexView(TemplateView):
    template_name = "championship/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = get_leaderboard(settings.DEFAULT_SEASON)[:PLAYERS_TOP]
        context["future_events"] = self._future_events()
        context["partner_logos"] = self._partner_logos()
        context["has_open_invoices"] = self._has_open_invoices()
        return context

    def _future_events(self):
        future_events = (
            Event.objects.filter(date__gte=datetime.date.today())
            .exclude(category=Event.Category.REGULAR)
            .order_by("date")[:EVENTS_ON_PAGE]
            .select_related("organizer", "address")
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

    def _has_open_invoices(self) -> bool:
        if self.request.user.is_anonymous:
            return False

        return Invoice.objects.filter(
            event_organizer__user=self.request.user, payment_received_date__isnull=True
        ).exists()


LAST_RESULTS = "last_results"
TOP_FINISHES = "top_finishes"
QP_TABLE = "qp_table"
THEAD = "thead"
TBODY = "tbody"
TABLE = "table"
QPS = "QPs"
EVENTS = "Events"


def add_to_table(table, column_title, row_title, value=1):
    """Increases the entry of the table in the given column-row pair by the value."""
    thead = table[THEAD]
    if column_title not in thead:
        return
    column_index = thead.index(column_title)
    tbody = table[TBODY]
    for existing_row in tbody:
        if existing_row[0] == row_title:
            existing_row[column_index] += value
            return
    new_row = [row_title] + [0] * (len(thead) - 1)
    new_row[column_index] = value
    tbody.append(new_row)


class PlayerDetailsView(DetailView):
    template_name = "championship/player_details.html"
    model = Player
    context_object_name = "player"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        results = get_results_with_qps(
            EventPlayerResult.objects.filter(player=context["player"])
        )

        context[LAST_RESULTS] = sorted(
            results, key=lambda r: r[0].event.date, reverse=True
        )

        qp_table = {
            THEAD: [
                "",
                Event.Category.PREMIER.label,
                Event.Category.REGIONAL.label,
                Event.Category.REGULAR.label,
                "Total",
            ],
            TBODY: [],
        }
        with_top_8_table = {
            THEAD: ["", Event.Category.PREMIER.label, Event.Category.REGIONAL.label],
            TBODY: [],
        }
        without_top_8_table = {
            THEAD: ["", Event.Category.REGIONAL.label, Event.Category.REGULAR.label],
            TBODY: [],
        }
        for result, score in sorted(context[LAST_RESULTS]):
            add_to_table(
                qp_table,
                column_title=result.event.get_category_display(),
                row_title=QPS,
                value=score.qps,
            )
            add_to_table(
                qp_table,
                column_title=result.event.get_category_display(),
                row_title=EVENTS,
            )

            if result.has_top8:
                # For events with top 8 only display the results if the player made top 8
                if result.single_elimination_result:
                    add_to_table(
                        with_top_8_table,
                        column_title=result.event.get_category_display(),
                        row_title=result.get_ranking_display(),
                    )
            else:
                # For swiss rounds only display top 3 finishes
                if result.ranking < 4:
                    add_to_table(
                        without_top_8_table,
                        column_title=result.event.get_category_display(),
                        row_title=result.get_ranking_display(),
                    )

        if len(qp_table[TBODY]) > 0:
            # Compute the total and add it in the last column
            for row in qp_table[TBODY]:
                row[-1] = sum(row[1:])

            context[QP_TABLE] = qp_table

        context[TOP_FINISHES] = [
            {"title": "Top 8 Finishes", TABLE: with_top_8_table},
            {"title": "Best Swiss Round Finishes", TABLE: without_top_8_table},
        ]
        return context


class EventDetailsView(DetailView):
    template_name = "championship/event_details.html"
    model = Event
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        event = self.get_object()
        context = super().get_context_data(**kwargs)
        results = get_results_with_qps(
            EventPlayerResult.objects.filter(event=event).annotate(
                player_name=F("player__name"),
            )
        )

        context["can_edit_results"] = (
            event.can_be_edited() and event.organizer.user == self.request.user
        ) or self.request.user.is_superuser

        context["results"] = sorted(results)
        context["has_decklists"] = any(
            result.decklist_url for result, _ in context["results"]
        )

        # Prompt the players to notify the organizer that they forgot to upload results
        # Only do so when the event is finished longer than 4 days ago and results can still be uploaded.
        context["notify_missing_results"] = (
            context["event"].date < datetime.date.today() - datetime.timedelta(days=4)
            and context["event"].can_be_edited()
        )
        return context


class PerSeasonView(TemplateView):
    default_season = settings.DEFAULT_SEASON
    season_list = SEASON_LIST

    def dispatch(self, request, *args, **kwargs):
        self.slug = self.kwargs.get("slug", self.default_season.slug)
        try:
            self.current_season = find_season_by_slug(self.slug)
        except KeyError:
            raise Http404(f"Unknown season {self.slug}")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        # We return two templates so that in case the season-specific one is
        # not found, the default one gets returned.
        return [
            self.template_path.format(slug=s)
            for s in (self.slug, self.default_season.slug)
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seasons"] = self.season_list
        context["current_season"] = self.current_season
        context["view_name"] = self.season_view_name
        return context


class CompleteRankingView(PerSeasonView):
    template_path = "championship/ranking/{slug}/ranking.html"
    season_view_name = "ranking-by-season"
    season_list = SEASONS_WITH_RANKING

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = get_leaderboard(self.current_season)
        return context


class InformationForPlayerView(PerSeasonView):
    template_path = "championship/info/{slug}/info_player.html"
    season_view_name = "info_for_season"
    season_list = SEASONS_WITH_INFO


class InformationForOrganizerView(PerSeasonView):
    template_path = "championship/info/{slug}/info_organizer.html"
    season_view_name = "info_organizer_for_season"
    season_list = SEASONS_WITH_INFO


class CreateEventView(LoginRequiredMixin, FormView):
    template_name = "championship/create_event.html"
    form_class = EventCreateForm

    def get_form_kwargs(self):
        kwargs = super(CreateEventView, self).get_form_kwargs()
        kwargs["organizer"] = self.request.user.eventorganizer

        default_address = kwargs["organizer"].default_address
        if default_address:
            kwargs["initial"]["address"] = default_address.id
        return kwargs

    def form_valid(self, form):
        event = form.save(commit=False)
        event.organizer = self.request.user.eventorganizer
        event.save()

        messages.success(self.request, "Succesfully created event!")

        return HttpResponseRedirect(reverse("event_details", args=[event.id]))


@login_required
def copy_event(request, pk):
    original_event = get_object_or_404(Event, pk=pk)
    organizer = request.user.eventorganizer
    if request.method == "POST":
        form = EventCreateForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.pk = None  # Force django to commit
            event.organizer = organizer
            event.save()

            messages.success(request, "Succesfully created event!")

            return HttpResponseRedirect(reverse("event_details", args=[event.id]))
    else:
        # By default, copy it one week later
        new_event = get_object_or_404(Event, pk=pk)
        new_event.date += datetime.timedelta(days=7)
        form = EventCreateForm(instance=new_event, organizer=organizer)

    return render(
        request,
        "championship/copy_event.html",
        {"form": form, "original_event": original_event},
    )


@login_required
def update_event(request, pk):
    event = get_object_or_404(Event, pk=pk)

    # If the event can no longer be edited, the user should not see the edit button.
    if event.organizer.user != request.user or not event.can_be_edited():
        return HttpResponseForbidden()

    if request.method == "POST":
        form = EventCreateForm(request.POST, instance=event)
        if form.is_valid():
            # Before we save the event, we need to check if the event can still be edited on the new date.
            # This prevents TOs from moving present events with results to the past.
            event = form.save(commit=False)
            if event.can_be_edited():
                event.save()
                messages.success(request, "Succesfully saved event")
                return HttpResponseRedirect(reverse("event_details", args=[event.id]))
            else:
                messages.error(request, "Event date is too old.")
    else:
        form = EventCreateForm(instance=event, organizer=event.organizer)

    return render(
        request, "championship/update_event.html", {"form": form, "event": event}
    )


class EventDeleteView(CustomDeleteView):
    model = Event

    def get_success_url(self):
        return reverse("organizer_details", args=[self.object.organizer.id])

    def allowed_to_delete(self, event, request):
        return event.can_be_deleted() and event.organizer.user == request.user


def validate_standings_and_show_error(request, standings, category):
    """
    Validates the standings for a given category and sends a given error message to the UI.

    Args:
        standings (list): A list of tuples containing player names and their respective points.
        category (Event.Category): The category of the event.

    Returns:
        True: When an error html should be rendered for the user.
    """
    try:
        validate_standings(standings, category)
    except TooFewPlayersForPremierError as e:
        messages.error(request, e.ui_error_message())
        return True
    except (
        TooManyPointsForPlayerError,
        TooManyPointsInTotalError,
        TooManyPointsForTop8Error,
    ) as e:
        if category == Event.Category.REGULAR:
            error_message = f"{e.ui_error_message()} You're trying to upload a SUL Regular event with more than 6 Swiss rounds. Please contact us at leoninleague@gmail.com!"
        else:
            error_message = f"{e.ui_error_message()} {get_max_round_error_message(category, standings)} Please use the standings of the last Swiss round!"
        messages.error(request, error_message)
        return True
    return False


def clean_name(name: str) -> str:
    """Normalizes the given name based on observations from results uploaded.

    This function applies transformations to the provided input so that the
    result is a clean name ready to be put in the DB.

    For example, all of the following inputs map to the normalized "Antoine Albertelli":

    CamelCase:
    >>> clean_name('AntoineAlbertelli')
    'Antoine Albertelli'

    All caps
    >>> clean_name('Antoine ALBERTELLI')
    'Antoine Albertelli'

    Snake Case
    >>> clean_name('Antoine_Albertelli')
    'Antoine Albertelli'

    Extra spaces
    >>> clean_name('   Antoine   Albertelli')
    'Antoine Albertelli'

    All lower caps
    >>> clean_name('antoine albertelli')
    'Antoine Albertelli'


    Note lower case words are only capitalized if the word has more than 3 letters
    (Short terms like "van", ""der", "da" shouldn't be capital).
    >>> clean_name('Antoine van Albertelli')
    'Antoine van Albertelli'

    >>> clean_name('Antoine J. Albertelli')
    'Antoine J. Albertelli'
    """
    name = name.replace("_", " ")
    name = re.sub(
        r"([A-Z])([A-Z]+)", lambda match: match.group(1) + match.group(2).lower(), name
    )
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    # Normalizes whitespace in case there are double space or tabs
    name = re.sub(r"\s+", " ", name)
    name = name.strip()
    # Capitalizes all words with 4 or more letters or that end with a dot "."
    name = " ".join(
        [
            word.title() if len(word) > 3 or word.endswith(".") else word
            for word in name.split()
        ]
    )
    return name


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

    @transaction.atomic
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
            return self.form_invalid(form)

        # Sometimes the webpages or users don't sort the standings correctly. Hence we should sort as a precaution.
        standings.sort(key=lambda pr: pr.points, reverse=True)

        # Check that the records amount to the same amount of match points
        for parse_result in standings:
            (w, l, d) = parse_result.record
            points = parse_result.points
            if points != w * 3 + d:
                messages.error(
                    self.request,
                    f"""The record of {parse_result.name} does not add up to the match points. Please send us 
                    the results link or file via email to leoninleague@gmail.com""",
                )
                return self.form_invalid(form)

        if self.event.results_validation_enabled and validate_standings_and_show_error(
            self.request,
            [(pr.name, pr.points, pr.record) for pr in standings],
            self.event.category,
        ):
            return self.form_invalid(form)

        for i, parse_result in enumerate(standings):
            (w, l, d) = parse_result.record
            name = clean_name(parse_result.name)
            try:
                player = PlayerAlias.objects.get(name=name).true_player
            except PlayerAlias.DoesNotExist:
                player, _ = Player.objects.get_or_create(name=name)

            EventPlayerResult.objects.create(
                points=parse_result.points,
                player=player,
                event=self.event,
                ranking=i + 1,
                win_count=w,
                loss_count=l,
                draw_count=d,
                decklist_url=parse_result.decklist_url,
                deck_name=parse_result.deck_name if parse_result.deck_name else "",
            )

        return super().form_valid(form)

    def get_success_url(self):
        return self.event.get_absolute_url()


class CreateManualResultsView(LoginRequiredMixin, CreateResultsView):
    template_name = "championship/create_results_manual.html"

    def get_context_data(self, formset=None, metadata_form=None):
        if not formset:
            formset = ResultsFormset()

        if not metadata_form:
            metadata_form = ManualUploadMetadataForm(user=self.request.user)

        players = Player.leaderboard_objects.all()

        return {
            "metadata_form": metadata_form,
            "formset": formset,
            "players": players,
        }

    def form_invalid(self, form):
        context = self.get_context_data(metadata_form=form, formset=self.formset)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.formset = ResultsFormset(request.POST)
        metadata_form = ManualUploadMetadataForm(user=request.user, data=request.POST)

        if not self.formset.is_valid() or not metadata_form.is_valid():
            return self.form_invalid(metadata_form)
        return self.form_valid(metadata_form)

    def get_results(self, form):
        standings = []
        for result in self.formset.cleaned_data:
            name = result.get("name")
            record = result.get("points")
            if name and record:
                pr = ParseResult(
                    name=name,
                    points=record_to_points(record),
                    record=parse_record(record),
                )
                standings.append(pr)
        return standings


class CreateLinkParserResultsView(LoginRequiredMixin, CreateResultsView):
    form_class = LinkImporterForm
    help_text: str
    placeholder: str

    def clean_url(self, url):
        raise NotImplementedError("This method has not been implemented yet.")

    def extract_standings_from_page(self, text: str) -> Iterable[tuple[str, int]]:
        raise NotImplementedError("No parser yet")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"help_text": self.help_text, "placeholder": self.placeholder})
        return kwargs

    def get_results(self, form):
        url = form.cleaned_data["url"]
        url = self.clean_url(url)
        if not url:
            messages.error(self.request, "Wrong url format.")
            return
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return list(self.extract_standings_from_page(response.content.decode()))
        except:
            messages.error(self.request, "Could not fetch standings.")


class CreateFileParserResultsView(LoginRequiredMixin, CreateResultsView):
    form_class = FileImporterForm
    help_text = "The file that contains the standings."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"help_text": self.help_text})
        return kwargs


class CreateHTMLParserResultsView(CreateFileParserResultsView):
    help_text = (
        "The standings file saved as a web page (.html). "
        + "Go to the standings page of the last swiss round, then press Ctrl+S and save."
    )
    error_text = (
        "Error: Could not parse standings file. Did you upload it as HTML? "
        + "You can get a HTML file by going to the standings of the last swiss round and pressing Ctrl+S."
    )

    def extract_standings_from_page(self, text: str) -> Iterable[tuple[str, int]]:
        raise NotImplementedError("No parser yet")

    def get_results(self, form):
        try:
            text = "".join(s.decode() for s in self.request.FILES["standings"].chunks())
            return self.extract_standings_from_page(text)
        except Exception as e:
            logging.exception("Could not parse page")
            messages.error(self.request, self.error_text)


class CreateAetherhubResultsView(CreateLinkParserResultsView):
    help_text = (
        "Link to your tournament. Make sure it is a public and finished tournament."
    )
    placeholder = "https://aetherhub.com/Tourney/RoundTourney/123456"

    def extract_standings_from_page(self, text):
        return aetherhub.parse_standings_page(text)

    def clean_url(self, url):
        """Normalizes the given tournament url to point to the RoundTourney page."""
        url_re = r"https://aetherhub.com/Tourney/[a-zA-Z]+/(\d+)"
        tourney = re.match(url_re, url)
        if tourney:
            return f"https://aetherhub.com/Tourney/RoundTourney/{tourney.group(1)}"


class CreateChallongeResultsView(CreateLinkParserResultsView):
    help_text = (
        "Link to your tournament. Make sure the tournament system is Swiss rounds."
    )
    placeholder = "https://challonge.com/de/rk6vluaa"

    def extract_standings_from_page(self, text):
        return challonge.parse_standings_page(text)

    def clean_url(self, url):
        try:
            return challonge.clean_url(url)
        except ValueError:
            pass


class CreateEventlinkResultsView(CreateHTMLParserResultsView):
    def extract_standings_from_page(self, text):
        return eventlink.parse_standings_page(text)


class CreateMtgEventResultsView(CreateHTMLParserResultsView):
    def extract_standings_from_page(self, text):
        return mtgevent.parse_standings_page(text)


class CreateExcelCsvResultsView(CreateFileParserResultsView):
    help_text = (
        "Upload an Excel (.xlsx) or CSV (.csv) file. The headers of the columns need to be named in a specific way: "
        + "PLAYER_NAME for the column with the name of the player. "
        + "RECORD for the record of the player. "
        + "You can also use the column MATCH_POINTS if you only have the match points and no record."
    )

    def _read_excel_csv(self):
        try:
            file = self.request.FILES["standings"]
            file_buffer = io.BytesIO(file.read())
            df = pd.read_excel(file_buffer, engine="openpyxl")
        except BadZipFile:
            try:
                file_buffer.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(file_buffer.read(1024).decode()).delimiter
                file_buffer.seek(0)
                df = pd.read_csv(file_buffer, delimiter=delimiter)
            except (csv.Error, UnicodeDecodeError, pd.errors.ParserError):
                df = None
        return df

    def get_results(self, form):
        error_text = "Error in reading the file. Did you upload a .xlsx or .csv file with the headers of the columns named PLAYER_NAME and RECORD (or MATCH_POINTS)?"
        df = self._read_excel_csv()
        if df is None:
            logging.exception("Could not parse file as Excel or CSV")
            messages.error(self.request, error_text)
            return
        try:
            return excel_csv_parser.parse_standings_page(df)
        except Exception as e:
            logging.exception("Error parsing dataframe")
            if hasattr(e, "ui_error_message"):
                error_text = e.ui_error_message
            else:
                raise e
        messages.error(self.request, error_text)


class CreateMeleeResultsView(CreateFileParserResultsView):
    help_text = "Upload the standings exported by clicking on 'Export All Standings' in Melee's Tournament Controller's Standings page (.csv file)."

    def get_results(self, form):
        text = "".join(s.decode() for s in self.request.FILES["standings"].chunks())
        return melee.parse_standings(text)


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

    @transaction.atomic
    def form_valid(self, form):
        self.event = Event.objects.get(id=self.kwargs["pk"])

        if self.event.category == Event.Category.REGULAR:
            messages.error(self.request, "Top 8 are not allowed at SUL Regular.")
            return super().form_valid(form)

        if not self.event.can_be_edited():
            messages.error(
                self.request, "Event too old to add or change the playoffs results."
            )
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

        playoff_results_filled = [
            (form.cleaned_data[key], single_elim_result)
            for key, single_elim_result in FIELDS_TO_RESULTS.items()
            if form.cleaned_data[key] is not None
        ]

        if len(playoff_results_filled) not in [4, 8]:
            messages.error(self.request, "You need to fill in 4 or 8 playoff results.")
            return super().form_invalid(form)

        counter = Counter([epr for epr, _ in playoff_results_filled])
        duplicates = [result for result, count in counter.items() if count > 1]
        if duplicates:
            messages.error(
                self.request,
                f"Player '{duplicates[0].player.name}'has more than 1 result.",
            )
            return super().form_invalid(form)

        self.event.eventplayerresult_set.update(single_elimination_result=None)
        for event_player_result, single_elim_result in playoff_results_filled:
            event_player_result.single_elimination_result = single_elim_result
            event_player_result.save()

        return super().form_valid(form)

    def get_success_url(self):
        return self.event.get_absolute_url()


class ClearEventResultsView(LoginRequiredMixin, FormView):
    template_name = "championship/results_confirm_delete.html"
    form_class = ResultsDeleteForm

    def get_event(self) -> Event:
        return get_object_or_404(
            Event, id=self.kwargs["pk"], organizer__user=self.request.user
        )

    def get_success_url(self):
        return self.get_event().get_absolute_url()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["event"] = self.get_event()
        return ctx

    def form_valid(self, form):
        # No processing to do here, just delete results
        event = self.get_event()

        if event.can_be_edited():
            event.eventplayerresult_set.all().delete()
        else:
            messages.error(self.request, "Event too old to delete results.")

        return super().form_valid(form)


def update_ranking_order(event):
    """Updates the order of the ranking after a result has been updated."""
    results = EventPlayerResult.objects.filter(event=event)
    results = sorted(
        results, key=lambda r: (r.win_count, r.draw_count, -r.ranking), reverse=True
    )
    for i, result in enumerate(results):
        result.ranking = i + 1
        result.save()


class ResultUpdateView(UpdateView):
    model = EventPlayerResult
    form_class = EventPlayerResultForm
    template_name = "championship/update_result.html"

    def dispatch(self, request, *args, **kwargs):
        event = self.get_object().event
        organizer_allowed_to_edit = (
            request.user == event.organizer.user and event.can_be_edited()
        )
        if request.user.is_superuser or organizer_allowed_to_edit:
            return super().dispatch(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    @transaction.atomic
    def form_valid(self, form):
        old_player = self.get_object().player
        form.save()
        # Delete the old player if they have no results anymore
        results_old_player = EventPlayerResult.objects.filter(player=old_player)
        if not results_old_player:
            old_player.delete()
        update_ranking_order(form.instance.event)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("event_details", args=[self.object.event.id])


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
        qs = qs.select_related("organizer", "address", "organizer__default_address")
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
        qs = qs.select_related("organizer", "address", "organizer__default_address")
        return qs.order_by("-date")


class AutoCompletePlayerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that yields a list of players matching the search_name.
    """

    serializer_class = PlayerAutocompleteSerializer

    def get_queryset(self):
        search_name = self.request.query_params.get("search_name", "")
        players = Player.objects.filter(name__icontains=search_name).order_by("name")[
            :10
        ]
        return players


class ListFormats(viewsets.ViewSet):
    """API Endpoint returning all the formats we play in the league."""

    def list(self, request, format=None):
        return Response(sorted(Event.Format.labels))


class FutureEventView(TemplateView):
    template_name = "championship/future_events.html"


class EventOrganizerDetailView(DetailView):
    model = EventOrganizer
    template_name = "championship/organizer_details.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organizer = self.get_object()

        future_events = Event.objects.filter(
            organizer=organizer, date__gte=datetime.date.today()
        ).order_by("date")
        past_events = (
            Event.objects.filter(organizer=organizer, date__lt=datetime.date.today())
            .annotate(num_players=Count("eventplayerresult"))
            .order_by("-date")
        )

        all_events = []
        if future_events:
            all_events.append({"title": "Upcoming Events", "list": future_events})
        if past_events:
            all_events.append(
                {"title": "Past Events", "list": past_events, "has_num_players": True}
            )
        context["all_events"] = all_events
        return context


class OrganizerProfileEditView(LoginRequiredMixin, UpdateView):
    template_name = "championship/update_organizer.html"
    form_class = OrganizerProfileEditForm

    def get_object(self):
        return get_object_or_404(EventOrganizer, user=self.request.user)

    def get_success_url(self):
        return self.get_object().get_absolute_url()

    def form_valid(self, form):
        messages.success(self.request, "Succesfully updated organizer profile!")
        return super().form_valid(form)


class OrganizerListView(ListView):
    template_name = "championship/organizer_list.html"
    context_object_name = "organizers"

    def get_queryset(self):
        organizers = (
            EventOrganizer.objects.select_related("default_address")
            .annotate(num_events=Count("event"))
            .filter(num_events__gt=0)
            .order_by("name")
            .all()
        )
        organizers_with_address = [o for o in organizers if o.default_address]
        organizers_without_address = [o for o in organizers if not o.default_address]
        return (
            sorted(organizers_with_address, key=lambda o: o.default_address)
            + organizers_without_address
        )


class AddressListView(LoginRequiredMixin, ListView):
    model = Address
    template_name = "championship/address_list.html"

    def get_queryset(self):
        return self.request.user.eventorganizer.get_addresses()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organizer_url"] = self.request.user.eventorganizer.get_absolute_url()
        return context


class AddressViewMixin:
    model = Address
    form_class = AddressForm
    template_name = "championship/address_form.html"
    success_url = reverse_lazy("address_list")

    def form_valid(self, form):
        organizer = self.request.user.eventorganizer
        form.instance.organizer = organizer
        self.object = form.save()
        if form.cleaned_data["set_as_organizer_address"]:
            organizer.default_address = self.object
            organizer.save()
        return super().form_valid(form)


class AddressCreateView(LoginRequiredMixin, AddressViewMixin, CreateView):
    pass


class AddressUpdateView(LoginRequiredMixin, AddressViewMixin, UpdateView):
    def get_queryset(self):
        return self.request.user.eventorganizer.get_addresses()


class AddressDeleteView(CustomDeleteView):
    model = Address
    success_url = reverse_lazy("address_list")

    def allowed_to_delete(self, address, request):
        return address.organizer.user == request.user
