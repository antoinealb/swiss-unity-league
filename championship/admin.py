from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import reverse
from django import forms
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
        "organizer",
    )
    inlines = [ResultInline]
    search_fields = ["name", "organizer__name", "url"]
    list_filter = ["organizer", "category"]


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

                for e in EventPlayerResult.objects.filter(player=player):
                    e.player = original_player
                    e.save()
                player.delete()

            return redirect(
                "admin:championship_player_change",
                object_id=original_player.id,
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


admin.site.register(Player, PlayerAdmin)
admin.site.register(EventOrganizer)

admin.site.site_title = "Unity League"
admin.site.site_header = "Unity League Admin"
