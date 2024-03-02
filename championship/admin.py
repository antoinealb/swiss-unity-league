import datetime
import logging
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django import forms
from django.conf import settings
from django.contrib import messages
import pandas as pd
from championship import views

from .models import *
from championship.score import get_leaderboard
from invoicing.models import Invoice, PayeeAddress
from django.urls import path


class ResultInline(admin.TabularInline):
    model = EventPlayerResult
    extra = 0
    ordering = ("-event__date", "-points")


class PlayerAliasInline(admin.TabularInline):
    model = PlayerAlias
    extra = 1
    ordering = ("name",)


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
    num_of_players = forms.IntegerField(initial=32, min_value=1)


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
    list_per_page = 2000

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
            # TODO: Expose other seasons here
            top_players = get_leaderboard(settings.DEFAULT_SEASON)[:num_of_players]
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

    def upload_emails_eventfrog(self, request):

        def find_email_column_index(df):
            for col in df.columns:
                if df[col].apply(lambda x: "@" in str(x) and "." in str(x)).any():
                    return df.columns.get_loc(col)

        if request.method == "POST":
            form = EventfrogFileUploadForm(request.POST, request.FILES)
            if form.is_valid():
                excel_file = request.FILES["file"]
                try:
                    df = pd.read_excel(excel_file)
                    email_index = find_email_column_index(df)
                    if email_index is None:
                        self.message_user(request, "No email column found in the file.")
                    else:
                        first_name_index = email_index - 2
                        last_name_index = email_index - 1
                        player_names_and_emails = [
                            (
                                views.clean_name(
                                    f"{row[first_name_index]} {row[last_name_index]}"
                                ),
                                row[email_index],
                            )
                            for _, row in df.iterrows()
                        ]
                        # Remove rows with no email
                        player_names_and_emails = [
                            (name, email)
                            for name, email in player_names_and_emails
                            if pd.notna(email)
                        ]
                        player_names = [name for name, _ in player_names_and_emails]
                        matching_players = Player.objects.filter(name__in=player_names)

                        for player_name, email in player_names_and_emails:
                            player = matching_players.filter(name=player_name).first()
                            if player:
                                player.email = email
                                player.save()

                        self.message_user(
                            request, "Excel file has been processed successfully."
                        )
                        return HttpResponseRedirect(
                            reverse("admin:championship_player_changelist")
                        )
                except Exception as e:
                    self.message_user(request, "Error processing the file")
                    logging.exception("Error processing the file")
        else:
            form = EventfrogFileUploadForm()
        return render(request, "admin/eventfrog_email_upload.html", {"form": form})

    @admin.action(
        description="Merge selected players",
        permissions=["delete"],
    )
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
                for e in EventPlayerResult.objects.filter(player=player):
                    e.player = original_player
                    e.save()

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

        results = EventPlayerResult.objects.filter(player__in=players)
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
            .annotate(result_cnt=Count("eventplayerresult"))
            .exclude(result_cnt=0)
            .order_by("-date")
        )

        if event.count() > 0:
            return event[0].date
        return "No published results"


admin.site.register(EventOrganizer, EventOrganizerAdmin)

admin.site.site_title = "Unity League"

if settings.DEBUG:
    admin.site.site_header = "Unity League Admin (DEBUG)"
else:
    admin.site.site_header = "Unity League Admin"
