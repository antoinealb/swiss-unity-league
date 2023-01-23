from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import reverse
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


class PlayerAdmin(admin.ModelAdmin):
    inlines = [ResultInline]
    search_fields = ["name"]
    list_display = ["name"]
    actions = ["merge_players"]

    @admin.action(
        description="Merge selected players, keeping the oldest one.",
        permissions=["delete"],
    )
    def merge_players(self, request, queryset):
        players = list(queryset.order_by("id"))
        original_player = players[0]

        if "post" in request.POST:
            for player in players[1:]:
                for e in EventPlayerResult.objects.filter(player=player):
                    e.player = original_player
                    e.save()
                player.delete()

            return redirect(
                "admin:championship_player_change",
                object_id=original_player.id,
            )

        else:
            results = sum(
                (list(EventPlayerResult.objects.filter(player=p)) for p in players), []
            )

            return render(
                request,
                "admin/merge_confirmation.html",
                context={
                    "players": players,
                    "results": results,
                    "original_player": original_player,
                    "action": request.POST["action"],
                },
            )


admin.site.register(Player, PlayerAdmin)
admin.site.register(EventOrganizer)

admin.site.site_title = "Unity League"
admin.site.site_header = "Unity League Admin"
