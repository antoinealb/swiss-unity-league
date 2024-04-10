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
from django.db.models import QuerySet
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
    list_display = (
        "name",
        "owner_name",
        "submission_deadline",
        "publication_time",
    )
    list_filter = ["event__organizer", DecklistPublishedListFilter]

    @admin.display(ordering="event__organizer__name", description="Owner name")
    def owner_name(self, instance: decklists.models.Collection) -> str:
        return instance.event.organizer.name


admin.site.register(decklists.models.Collection, CollectionAdmin)
admin.site.register(decklists.models.Decklist)
