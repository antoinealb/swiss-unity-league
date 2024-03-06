from championship.season import SEASONS_WITH_INFO
from championship.views.base import PerSeasonView


class InformationForPlayerView(PerSeasonView):
    template_path = "championship/info/{slug}/info_player.html"
    season_view_name = "info_for_season"
    season_list = SEASONS_WITH_INFO


class InformationForOrganizerView(PerSeasonView):
    template_path = "championship/info/{slug}/info_organizer.html"
    season_view_name = "info_organizer_for_season"
    season_list = SEASONS_WITH_INFO
