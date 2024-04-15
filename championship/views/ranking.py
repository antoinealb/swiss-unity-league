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

from django.views.generic.base import TemplateView

from championship.score import get_leaderboard
from championship.season import SEASONS_WITH_RANKING
from championship.views.base import PerSeasonMixin


class CompleteRankingView(PerSeasonMixin, TemplateView):
    template_path = "championship/ranking/{slug}/ranking.html"
    season_view_name = "ranking-by-season"
    season_list = SEASONS_WITH_RANKING

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = get_leaderboard(self.current_season)
        return context
