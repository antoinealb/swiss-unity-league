from django.contrib import admin
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


admin.site.register(Player, PlayerAdmin)
admin.site.register(EventOrganizer)

admin.site.site_title = "Unity League"
admin.site.site_header = "Unity League Admin"
