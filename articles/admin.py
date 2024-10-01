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
from django.db.models import Q, QuerySet
from django.db.models.functions import Concat
from django.utils import timezone

import articles.models


class ArticlePublishedListFilter(admin.SimpleListFilter):
    title = "Publication status"
    parameter_name = "published"

    def lookups(self, request, model_admin):
        return [("published", "Published"), ("private", "Unpublished")]

    def queryset(self, request, queryset: QuerySet[articles.models.Article]):
        now = timezone.now()
        if self.value() == "published":
            return queryset.filter(publication_time__lte=now)
        elif self.value() == "private":
            return queryset.filter(
                Q(publication_time__gte=now) | Q(publication_time__isnull=True)
            )


class ArticleAdmin(admin.ModelAdmin):
    date_hierarchy = "last_changed"

    @admin.display(
        ordering=Concat("author__first_name", "author__last_name"),
        description="Author name",
    )
    def author_name(self, instance: articles.models.Article) -> str:
        first, last = instance.author.first_name, instance.author.last_name
        return f"{first} {last}"

    list_display = (
        "title",
        "author_name",
        "last_changed",
        "publication_time",
    )
    list_filter = [ArticlePublishedListFilter]
    fields = [
        "author",
        "title",
        "content",
        "publication_time",
    ]


admin.site.register(articles.models.Article, ArticleAdmin)
