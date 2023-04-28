from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import reverse
from django import forms
from django.conf import settings
from django.contrib import messages
from .models import *


class ResultInline(admin.TabularInline):
    model = EventPlayerResult
    extra = 0
    ordering = ("-event__date", "-points")


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
    inlines = [ResultInline]
    search_fields = ["name"]
    list_display = ["name"]
    actions = ["merge_players"]

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


class EventOrganizerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "last_event_with_results",
        "user",
    )

    sortable_by = ["name"]

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
