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

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.views.generic.edit import DeleteView

from championship.season import SEASON_LIST, find_season_by_slug


class PerSeasonMixin:
    default_season = settings.DEFAULT_SEASON
    season_list = SEASON_LIST

    def dispatch(self, request, *args, **kwargs):
        self.slug = self.kwargs.get("slug", self.default_season.slug)
        try:
            self.current_season = find_season_by_slug(self.slug)
        except KeyError:
            raise Http404(f"Unknown season {self.slug}")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        # We return two templates so that in case the season-specific one is
        # not found, the default one gets returned.
        return [
            self.template_path.format(slug=s)
            for s in (self.slug, self.default_season.slug)
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["seasons"] = self.season_list
        context["current_season"] = self.current_season
        context["view_name"] = self.season_view_name
        return context


class CustomDeleteView(LoginRequiredMixin, DeleteView):
    success_message = "Successfully deleted {verbose_name}!"

    def allowed_to_delete(self, object, request):
        return True

    def dispatch(self, request, *args, **kwargs):
        if not self.allowed_to_delete(self.get_object(), request):
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        request = self.request
        verbose_name = self.object._meta.verbose_name.lower()
        messages.success(
            request, self.success_message.format(verbose_name=verbose_name)
        )
        self.delete(self.request)
        return HttpResponseRedirect(self.get_success_url())
