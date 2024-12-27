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

from django.contrib import admin
from django.db.models import Case, F, QuerySet, When
from django.utils import timezone

import decklists.models


class DecklistPublishedListFilter(admin.SimpleListFilter):
    title = "decklist publication status"
    parameter_name = "published"

    def lookups(self, request, model_admin):
        return [("published", "Published"), ("private", "Unpublished")]

    def queryset(self, request, queryset: QuerySet[decklists.models.Collection]):
        now = timezone.now()
        if self.value() == "published":
            return queryset.filter(publication_time__lte=now)
        if self.value() == "private":
            return queryset.filter(publication_time__gte=now)


class CollectionAdmin(admin.ModelAdmin):
    date_hierarchy = "submission_deadline"
    autocomplete_fields = ["event"]
    list_display = (
        "name",
        "owner_name",
        "get_format_display",
        "submission_deadline",
        "publication_time",
    )
    list_filter = ["event__organizer", DecklistPublishedListFilter]
    exclude = ["staff_key"]

    @admin.display(ordering="event__organizer__name", description="Owner name")
    def owner_name(self, instance: decklists.models.Collection) -> str:
        return instance.event.organizer.name

    @admin.display(description="Format", ordering="_format_ordering")
    def get_format_display(self, instance: decklists.models.Collection) -> str:
        return instance.get_format_display()

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return qs.annotate(
            _format_ordering=Case(
                When(format_override__isnull=False, then=F("format_override")),
                default=F("event__format"),
            )
        )


admin.site.register(decklists.models.Collection, CollectionAdmin)


class DecklistAdmin(admin.ModelAdmin):
    @admin.display(description="Collection name", ordering="collection__name")
    def collection_name(self, obj):
        return obj.collection.name

    @admin.display(
        description="Event Organizer", ordering="collection__event__organizer__name"
    )
    def event_organizer(self, obj):
        return obj.collection.event.organizer.name

    @admin.display(description="Event", ordering="collection__event__name")
    def event_name(self, obj):
        return obj.collection.event.name

    @admin.display(description="Player", ordering="player__name")
    def player_name(self, obj):
        return obj.player.name

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return qs.select_related(
            "collection", "collection__event", "collection__event__organizer", "player"
        )

    list_display = [
        "last_modified",
        "player_name",
        "event_organizer",
        "event_name",
        "collection_name",
    ]
    ordering = ["-last_modified"]
    search_fields = ["player__name"]


admin.site.register(decklists.models.Decklist, DecklistAdmin)
