from django.urls import reverse
from django.views.generic import TemplateView

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


class IcalInformationView(TemplateView):
    template_name = "championship/info/ical.html"

    def events_url(self, view_name: str) -> str:
        return self.request.build_absolute_uri(reverse(view_name))

    def get_context_data(self):
        return {
            "premier_events_url": self.events_url("premier_events_feed"),
            "regional_events_url": self.events_url("events_feed"),
            "all_events_url": self.events_url("all_events_feed"),
        }
