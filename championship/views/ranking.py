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
from django.contrib.sites.models import Site
from django.urls import reverse
from django.views.generic.base import TemplateView

from championship.score import get_leaderboard
from championship.seasons.definitions import Season
from championship.seasons.helpers import get_seasons_with_scores
from championship.views.base import PerSeasonMixin
from multisite.constants import SWISS_DOMAIN


class CompleteRankingView(PerSeasonMixin, TemplateView):
    template_path = "championship/ranking/{slug}/ranking.html"

    def get_season_list(self):
        return get_seasons_with_scores()

    def get_country_code(self) -> str:
        if Site.objects.get_current().domain == SWISS_DOMAIN:
            return "CH"
        return self.kwargs.get("country_code", settings.DEFAULT_COUNTRY)

    def get_url_for_season(self, season: Season) -> str:
        return reverse(
            "ranking_by_season_country",
            kwargs={
                "slug": season.slug,
                "country_code": self.get_country_code(),
            },
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = get_leaderboard(
            self.current_season, self.get_country_code()
        )
        return context
