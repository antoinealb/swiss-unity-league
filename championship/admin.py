# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import warnings

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import path, reverse

import openpyxl

from championship.score import get_leaderboard
from championship.seasons.helpers import (
    find_season_by_slug,
    get_default_season,
    get_seasons_with_scores,
)
from decklists.models import Decklist
from invoicing.models import Invoice, PayeeAddress

from .models import (
    Event,
    EventOrganizer,
    OrganizerLeague,
    Player,
    PlayerAlias,
    PlayerProfile,
    PlayerSeasonData,
    RecurrenceRule,
    RecurringEvent,
    Result,
    SpecialReward,
)


class SpecialRewardInline(admin.TabularInline):
    model = SpecialReward
    extra = 0


class ResultInline(admin.TabularInline):
    model = Result
    extra = 0
    ordering = ("-event__date", "-points")
    fields = [
        "player",
        "event",
        "ranking",
        "playoff_result",
        "points",
        "win_count",
        "loss_count",
        "draw_count",
        "deck_name",
        "decklist_url",
    ]
    readonly_fields = ["player", "event"]
    show_change_link = True


class PlayerAliasInline(admin.TabularInline):
    model = PlayerAlias
    extra = 1
    ordering = ("name",)


class ResultAdmin(admin.ModelAdmin):
    fields = [
        "player",
        "event",
        ("ranking", "points"),
        ("win_count", "loss_count", "draw_count"),
        "playoff_result",
    ]
    search_fields = [
        "player__name",
        "event__organizer__name",
        "event__category",
        "event__format",
    ]
    inlines = [SpecialRewardInline]


admin.site.register(Result, ResultAdmin)


class EventAdmin(admin.ModelAdmin):
    date_hierarchy = "date"
    list_display = (
        "name",
        "date",
        "category",
        "format",
        "organizer",
    )
    inlines = [ResultInline]
    search_fields = ["name", "organizer__name", "url"]
    list_filter = ["organizer", "category", "format"]


admin.site.register(Event, EventAdmin)


class RecurrenceRuleInline(admin.TabularInline):
    model = RecurrenceRule
    extra = 0


class RecurringEventAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")
    inlines = [RecurrenceRuleInline]


admin.site.register(RecurringEvent, RecurringEventAdmin)


class PlayerMergeForm(forms.Form):
    player_to_keep = forms.ModelChoiceField(
        queryset=Player.objects.all(),
        required=True,
        help_text="The player to keep, who will get all the results.",
    )

    def __init__(self, players, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["player_to_keep"].queryset = players
        self.fields["player_to_keep"].initial = players[0]


class TopPlayersEmailForm(forms.Form):
    num_of_players = forms.IntegerField(initial=40, min_value=1)
    season = forms.ChoiceField(
        choices=lambda: [(s.slug, s.name) for s in get_seasons_with_scores()],
        initial=lambda: get_default_season(),
    )


class EventfrogFileUploadForm(forms.Form):
    file = forms.FileField(
        help_text="The file you can export in the Eventfrog.ch dashboard under Sales > Orders, Cancellations > Export.",
        label="Eventfrog Excel file",
    )


class PlayerAdmin(admin.ModelAdmin):
    inlines = [ResultInline, PlayerAliasInline]
    search_fields = ["name"]
    list_display = ["name", "email"]
    actions = ["merge_players"]

    def get_search_results(self, request, queryset, search_term):
        """We search for players that contain at least one of the search terms."""
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        search_terms = search_term.split()
        if search_terms:
            query = Q(name__icontains=search_terms[0])
            for term in search_terms[1:]:
                query |= Q(name__icontains=term)
            queryset |= self.model.objects.filter(query)
        return queryset.distinct(), use_distinct

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "top_emails/",
                self.admin_site.admin_view(self.top_players_emails_view),
                name="top_players_emails",
            ),
            path(
                "email_upload/eventfrog",
                self.admin_site.admin_view(self.upload_emails_eventfrog),
                name="email_upload_eventfrog",
            ),
        ]
        return custom_urls + urls

    def top_players_emails_view(self, request):
        form = TopPlayersEmailForm(request.POST or None)
        context = {"form": form}
        if request.method == "POST" and form.is_valid():
            num_of_players = form.cleaned_data["num_of_players"]
            season = find_season_by_slug(form.cleaned_data["season"])
            top_players = get_leaderboard(season)[:num_of_players]
            entries = [
                {
                    "rank": i + 1,
                    "player": player.name,
                    "email": player.email if player.email else "",
                }
                for i, player in enumerate(top_players)
            ]
            emails = "; ".join(
                player.email
                for player in top_players
                if player.email and player.email != ""
            )
            context["entries"] = entries
            context["emails"] = emails
        return render(request, "admin/top_players_emails.html", context)

    @transaction.atomic
    def upload_emails_eventfrog(self, request):
        if request.method != "POST":
            form = EventfrogFileUploadForm()
            return render(request, "admin/eventfrog_email_upload.html", {"form": form})

        form = EventfrogFileUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "admin/eventfrog_email_upload.html", {"form": form})

        excel_file = request.FILES["file"]

        # openpyxl throws a warnings about styling of the sheet, which we don't
        # really care about.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sheet = openpyxl.load_workbook(excel_file).active

        rows = sheet.iter_rows()

        column_indices = {}
        for row in rows:
            if row[0].value != "Ticket ID":
                continue

            interesting_columns = {"First name", "Last name", "Email", "Status"}
            for i, c in enumerate(row):
                c = c.value
                if c in interesting_columns:
                    column_indices[c] = i
            break

        if "Email" not in column_indices:
            self.message_user(request, "No email column found in the file.")
            return render(request, "admin/eventfrog_email_upload.html", {"form": form})

        # Extract a list of (name, emails) tuple
        player_names_and_emails = []
        for row in rows:
            email = row[column_indices["Email"]].value
            if not email:
                continue

            first = row[column_indices["First name"]].value
            last = row[column_indices["Last name"]].value
            full = f"{first} {last}"
            player_names_and_emails.append((full, email))

        # Update all players
        for player_name, email in player_names_and_emails:
            Player.objects.filter(name=player_name).update(email=email)

        self.message_user(request, "Excel file has been processed successfully.")
        return HttpResponseRedirect(reverse("admin:championship_player_changelist"))

    @admin.action(
        description="Merge selected players",
        permissions=["delete"],
    )
    @transaction.atomic
    def merge_players(self, request, queryset):
        queryset = queryset.order_by("id")
        players = queryset.order_by("id")

        form = PlayerMergeForm(queryset, request.POST)

        if form.is_valid():
            original_player = form.cleaned_data["player_to_keep"]
            for player in players:
                if player == original_player:
                    continue

                # First, take all the results and attribute them back to the
                # original player.
                for e in Result.objects.filter(player=player):
                    e.player = original_player
                    e.save()

                # Then do the same for decklists
                for d in Decklist.objects.filter(player=player):
                    d.player = original_player
                    d.save()

                # Then, create an alias for the player
                PlayerAlias.objects.create(
                    name=player.name, true_player=original_player
                )

                # Merge the email if the original_player has no email yet
                if original_player.email == "" and player.email != "":
                    original_player.email = player.email
                    original_player.save()

                # Finally, delete the extra player
                player.delete()

            messages.add_message(
                request, messages.INFO, f"Succesfully saved {original_player.name}"
            )
            return redirect(
                "admin:championship_player_changelist",
            )

        results = Result.objects.filter(player__in=players)
        form = PlayerMergeForm(queryset)
        return render(
            request,
            "admin/merge_confirmation.html",
            context={
                "players": players,
                "results": results,
                "form": form,
                "action": request.POST["action"],
            },
        )


class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "player",
        "status",
        "consent_for_website",
        "consent_for_stream",
        "team_name",
    )
    search_fields = ["player__name"]
    autocomplete_fields = ["player"]
    list_filter = ["status"]

    def pronouns(self, obj):
        return obj.get_pronouns()

    def age(self, obj):
        return obj.age()


class PlayerSeasonDataAdmin(admin.ModelAdmin):
    list_display = (
        "player",
        "season_slug",
        "country",
        "auto_assign_country",
    )
    search_fields = ["player__name"]
    list_filter = ["season_slug", "country"]


class PlayerAliasAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "true_player_name",
    )
    search_fields = ["name", "true_player__name"]

    @admin.display(ordering="true_player__name", description="True player name")
    def true_player_name(self, instance):
        return instance.true_player.name


admin.site.register(PlayerAlias, PlayerAliasAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(PlayerProfile, PlayerProfileAdmin)
admin.site.register(PlayerSeasonData, PlayerSeasonDataAdmin)


def _last_day_of_month(any_day: datetime.date) -> datetime.date:
    """Returns the last day of the month of the given date.

    >>> _last_day_of_month(datetime.date(2023, 5, 10))
    datetime.date(2023, 5, 31)
    >>> _last_day_of_month(datetime.date(2023, 2, 10))
    datetime.date(2023, 2, 28)
    """
    # The day 28 exists in every month. 4 days later, it's always next month
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    # subtracting the number of the current day brings us back one month
    return next_month - datetime.timedelta(days=next_month.day)


class EventOrganizerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "last_event_with_results",
        "user",
    )

    sortable_by = ["name"]
    actions = ["create_invoices"]

    @admin.action(
        description="Create invoices for selected organizers",
        permissions=["invoice"],
    )
    def create_invoices(self, request, queryset):
        # We take the most recently created payee address (the one with the
        # highest ID).
        payee_address = PayeeAddress.objects.order_by("-id")[0]
        for organizer in queryset:
            last_invoice = (
                Invoice.objects.filter(event_organizer=organizer)
                .order_by("-end_date")
                .first()
            )

            if last_invoice:
                start_date = last_invoice.end_date + datetime.timedelta(days=1)
            else:
                # Start at first day of the SUL start
                start_date = datetime.date(2023, 1, 1)

            # Take the last day of previous month where its not allowed to
            # upload results anymore.
            end_date = _last_day_of_month(
                datetime.date.today()
                - datetime.timedelta(days=31)
                - settings.EVENT_MAX_AGE_FOR_RESULT_ENTRY
            )

            if start_date > end_date:
                messages.add_message(
                    request,
                    messages.WARNING,
                    f"Skipping {organizer.name} as the last invoice was too recent.",
                )
                continue

            invoice = Invoice(
                event_organizer=organizer,
                start_date=start_date,
                end_date=end_date,
                payee_address=payee_address,
            )

            if invoice.total_amount > 0:
                invoice.save()

    def has_invoice_permission(self, request):
        return request.user.has_perm("invoicing.add_invoice")

    @admin.display(description="Last event with published results")
    def last_event_with_results(self, instance):
        event = (
            Event.objects.filter(organizer=instance)
            .annotate(result_cnt=Count("result"))
            .exclude(result_cnt=0)
            .order_by("-date")
        )

        if event.count() > 0:
            return event[0].date
        return "No published results"


admin.site.register(EventOrganizer, EventOrganizerAdmin)


class OrganizerLeagueAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "organizer",
        "format",
        "category",
        "start_date",
        "end_date",
    ]

    def organizer(self, league):
        return f"{league.organizer.name}"


admin.site.register(OrganizerLeague, OrganizerLeagueAdmin)


admin.site.site_title = "Unity League"

if settings.DEBUG:
    admin.site.site_header = "Unity League Admin (DEBUG)"
else:
    admin.site.site_header = "Unity League Admin"
