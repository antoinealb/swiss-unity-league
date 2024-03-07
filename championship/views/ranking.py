from championship.score import get_leaderboard
from championship.season import SEASONS_WITH_RANKING
from championship.views.base import PerSeasonView


class CompleteRankingView(PerSeasonView):
    template_path = "championship/ranking/{slug}/ranking.html"
    season_view_name = "ranking-by-season"
    season_list = SEASONS_WITH_RANKING

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = get_leaderboard(self.current_season)
        return context
