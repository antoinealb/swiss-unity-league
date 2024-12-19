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

from dataclasses import asdict

from django.contrib import messages
from django.http import Http404, HttpResponseForbidden
from django.views.generic.edit import DeleteView

from championship.seasons.definitions import Season
from championship.seasons.helpers import (
    find_season_by_slug,
    get_default_season,
    get_main_seasons,
)


class PerSeasonMixin:
    template_path = ""

    def get_default_season(self) -> Season:
        return get_default_season()

    def get_season_list(self) -> list[Season]:
        return get_main_seasons()

    def get_url_for_season(self, season: Season) -> str:
        raise NotImplementedError()

    def dispatch(self, request, *args, **kwargs):
        self.slug = self.kwargs.get("slug", self.get_default_season().slug)
        try:
            self.current_season = find_season_by_slug(self.slug)
        except KeyError:
            raise Http404(f"Unknown season {self.slug}")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self) -> list[str]:
        # We return two templates so that in case the season-specific one is
        # not found, the default one gets returned.
        return [
            self.template_path.format(slug=s)
            for s in (self.slug, self.get_default_season().slug)
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seasons"] = [
            {**asdict(season), "url": self.get_url_for_season(season)}
            for season in self.get_season_list()
        ]
        context["current_season"] = self.current_season
        return context


class CustomDeleteView(DeleteView):
    success_message = "Successfully deleted {verbose_name}!"

    def allowed_to_delete(self, object, request):
        return True

    def dispatch(self, request, *args, **kwargs):
        if not self.allowed_to_delete(self.get_object(), request):
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, *args, **kwargs):
        verbose_name = self.object._meta.verbose_name.lower()
        messages.success(
            self.request, self.success_message.format(verbose_name=verbose_name)
        )
        return super().form_valid(*args, **kwargs)
