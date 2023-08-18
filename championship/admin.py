import datetime
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import reverse
from django import forms
from django.conf import settings
from django.contrib import messages

from championship.forms import TopPlayersEmailForm
from .models import *
from invoicing.models import Invoice
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
            )
        ]
        return custom_urls + urls

    def top_players_emails_view(self, request):
        form = TopPlayersEmailForm(request.POST or None)
        context = {"form": form}
        if request.method == "POST" and form.is_valid():
            num_of_players = form.cleaned_data["num_of_players"]
            players = list(Player.objects.all())
            scores_by_player = compute_scores()
            for p in players:
                p.score = scores_by_player[p.id]
            players.sort(key=lambda l: l.score, reverse=True)
            top_players = players[:num_of_players]
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
        for organizer in queryset:
            last_invoice = (
                Invoice.objects.filter(event_organizer=organizer)
                .order_by("-end_date")
                .first()
            )

            if last_invoice:
                start_date = last_invoice.end_date + datetime.timedelta(days=1)
            else:
                # Start at first day of the year
                start_date = datetime.date(datetime.date.today().year, 1, 1)

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
                event_organizer=organizer, start_date=start_date, end_date=end_date
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
