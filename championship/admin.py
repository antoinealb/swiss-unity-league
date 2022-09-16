from django.contrib import admin
from .models import *


class ResultInline(admin.TabularInline):
    model = EventPlayerResult
    extra = 0
    ordering = ("event__date", "ranking", "-points")


class EventAdmin(admin.ModelAdmin):
    date_hierarchy = "date"
    list_display = (
        "name",
        "date",
        "organizer",
    )
    inlines = [ResultInline]
    search_fields = ["name", "organizer__name", "url"]


admin.site.register(Event, EventAdmin)


class PlayerAdmin(admin.ModelAdmin):
    inlines = [ResultInline]
    search_fields = ["first_name", "last_name"]
    list_display = ["last_name", "first_name"]


admin.site.register(Player, PlayerAdmin)
admin.site.register(EventOrganizer)
