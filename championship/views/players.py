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

import dataclasses
from collections import Counter, defaultdict

from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, TemplateView

from championship.forms import PlayerProfileForm
from championship.models import Event, Player, PlayerProfile, Result
from championship.score import get_results_with_qps
from championship.seasons.helpers import get_seasons_with_scores
from championship.views.base import PerSeasonMixin
from decklists.models import Decklist

LAST_RESULTS = "last_results"
TOP_FINISHES = "top_finishes"
QP_TABLE = "qp_table"
THEAD = "thead"
TBODY = "tbody"
TABLE = "table"
QPS = "League Points"
EVENTS = "Events"
PERFORMANCE_PER_FORMAT = "performance_per_format"


@dataclasses.dataclass
class Performance:
    win: int = 0
    loss: int = 0
    draw: int = 0

    @property
    def win_ratio(self) -> float:
        try:
            return self.win / (self.win + self.loss + self.draw)
        except ZeroDivisionError:
            return 0.0

    @property
    def win_ratio_without_draws(self) -> float:
        try:
            return self.win / (self.win + self.loss)
        except ZeroDivisionError:
            return 0.0

    def __str__(self):
        return f"{self.win} - {self.loss} - {self.draw}"

    def __add__(self, other):
        return Performance(
            win=self.win + other.win,
            loss=self.loss + other.loss,
            draw=self.draw + other.draw,
        )


CATEGORY_ORDER = [
    Event.Category.GRAND_PRIX,
    Event.Category.QUALIFIER,
    Event.Category.PREMIER,
    Event.Category.REGIONAL,
    Event.Category.NATIONAL,
    Event.Category.REGULAR,
    Event.Category.OTHER,
]


def sorted_most_accomplished_results(results):
    def accomplishments_sort_key(result_score):
        result, score = result_score
        category_index = CATEGORY_ORDER.index(result.event.category)
        return (
            result.playoff_result or 16 + result.ranking,
            category_index,
            -result.event.date.toordinal(),
        )

    return sorted(
        results,
        key=accomplishments_sort_key,
    )


class PlayerDetailsView(PerSeasonMixin, DetailView):
    model = Player
    queryset = Player.objects.exclude(hidden_from_leaderboard=True)

    def get_url_for_season(self, season):
        return reverse(
            "player_details_by_season",
            kwargs={
                "slug": season.slug,
                "pk": self.object.pk,
            },
        )

    def get_season_list(self):
        return get_seasons_with_scores()

    def get_template_names(self):
        return ["championship/player_details.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context[LAST_RESULTS] = list(
            get_results_with_qps(
                Result.objects.filter(player=context["player"])
                .in_season(self.current_season)
                .prefetch_related("event__organizer")
                .order_by("-event__date")
            )
        )

        context["profile"] = (
            context["player"]
            .playerprofile_set.filter(
                status=PlayerProfile.Status.APPROVED, consent_for_website=True
            )
            .last()
        )
        organizer_counts = Counter(
            result.event.organizer.name for result, _ in context[LAST_RESULTS]
        )
        most_common_organizer = organizer_counts.most_common(1)
        context["local_organizer_name"] = (
            most_common_organizer[0][0] if most_common_organizer else None
        )

        if context["profile"]:

            context["accomplishments"] = sorted_most_accomplished_results(
                context[LAST_RESULTS]
            )[:3]

            context["accomplishments"] = sorted(
                context["accomplishments"], key=lambda r: r[0].event.date, reverse=True
            )

        context[PERFORMANCE_PER_FORMAT] = self.performance_per_format(
            context[LAST_RESULTS]
        )

        context[QP_TABLE] = self._get_qp_table(context)
        context["top_finish_table"] = self._get_top_finish_table(context)

        context["decklists"] = self._decklists(context["player"])
        return context

    def _get_top_finish_table(self, context):
        playoff_count_by_category_ranking = defaultdict(lambda: defaultdict(int))
        for result, _ in context[LAST_RESULTS]:
            if result.playoff_result:
                playoff_count_by_category_ranking[result.event.get_category_display()][
                    result.get_ranking_display()
                ] += 1
        rankings = sorted(
            set(
                r[0].get_ranking_display()
                for r in context[LAST_RESULTS]
                if r[0].playoff_result
            )
        )
        categories = [
            c.label
            for c in CATEGORY_ORDER
            if c.label in playoff_count_by_category_ranking
        ]
        with_top_8_table = {
            THEAD: [""] + categories,
            TBODY: [
                [ranking]
                + [
                    playoff_count_by_category_ranking[category].get(ranking, 0)
                    for category in categories
                ]
                for ranking in rankings
            ],
        }

        return {
            "title": "Top 8 Finishes",
            TABLE: with_top_8_table,
        }

    def _get_qp_table(self, context):
        qps_by_category = defaultdict(int)
        num_events_by_category = defaultdict(int)

        for result, score in sorted(
            context[LAST_RESULTS],
            key=lambda r: CATEGORY_ORDER.index(r[0].event.category),
        ):
            if score and score.qps:
                qps_by_category[result.event.get_category_display()] += score.qps
                num_events_by_category[result.event.get_category_display()] += 1

        categories = [c.label for c in CATEGORY_ORDER if c.label in qps_by_category]
        event_counts = [num_events_by_category[category] for category in categories]
        return {
            THEAD: [""] + categories + ["Total"],
            TBODY: [
                [QPS]
                + list(qps_by_category.values())
                + [sum(qps_by_category.values())],
                [EVENTS] + event_counts + [sum(event_counts)],
            ],
        }

    def _decklists(self, player):
        return (
            Decklist.objects.published()
            .filter(player=player)
            .select_related("collection__event")
            .order_by("-collection__event__date")
        )

    def performance_per_format(self, results) -> dict[str, Performance]:
        """Returns the peformance per format, with the display name of the format as key."""

        def extra_wins_for_top(result):
            if result.playoff_result is None:
                return 0

            points = {
                Result.PlayoffResult.WINNER: 3,
                Result.PlayoffResult.FINALIST: 2,
                Result.PlayoffResult.SEMI_FINALIST: 1,
                Result.PlayoffResult.QUARTER_FINALIST: 0,
            }[result.playoff_result]

            # If we are in top4, it means we had one less match to win to get
            # to any rank. We can ignore QUARTER_FINALIST being 0, as they
            # would not be present in a top4 only match.
            if result.top_count == 4:
                points -= 1

            return points

        def extra_losses_for_top(result):
            playoff_result = result.playoff_result
            if playoff_result in (None, Result.PlayoffResult.WINNER):
                return 0
            return 1

        perf_per_format: dict[str, Performance] = {}
        for result, _ in results:
            format = result.event.get_format_display()
            try:
                performance = perf_per_format[format]
            except KeyError:
                performance = Performance()
            performance.win += result.win_count + extra_wins_for_top(result)
            performance.loss += result.loss_count + extra_losses_for_top(result)
            performance.draw += result.draw_count
            perf_per_format[format] = performance

        perf_per_format["Overall"] = sum(perf_per_format.values(), start=Performance())

        return perf_per_format


class CreatePlayerProfileView(CreateView):
    model = PlayerProfile
    form_class = PlayerProfileForm
    template_name = "championship/create_player_profile.html"
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        messages.success(
            self.request, "Your player profile has been submitted for review."
        )
        return super().form_valid(form)


class PlayerProfilesByTeamView(TemplateView):
    template_name = "championship/player_profiles_by_team.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        player_profiles = PlayerProfile.objects.filter(
            status=PlayerProfile.Status.APPROVED, consent_for_website=True
        ).select_related("player")

        profiles_by_team = defaultdict(list)
        teamless_profiles = []
        for profile in player_profiles:
            if profile.team_name:
                profiles_by_team[profile.team_name].append(profile)
            else:
                teamless_profiles.append(profile)

        def profile_sort_key(profile):
            return (not profile.image, not profile.bio, profile.player.name.lower())

        for team in profiles_by_team:
            profiles_by_team[team].sort(key=profile_sort_key)

        teamless_profiles.sort(key=profile_sort_key)

        def team_sort_key(team):
            profiles = profiles_by_team[team]
            # Sort teams by most number of profiles with images and bios
            num_images = sum(1 for profile in profiles if profile.image)
            num_bios = sum(1 for profile in profiles if profile.bio)
            return (-num_images, -num_bios, team.lower())

        sorted_teams = sorted(profiles_by_team, key=team_sort_key)
        context["profiles_by_team"] = {
            team: profiles_by_team[team] for team in sorted_teams
        }
        context["teamless_profiles"] = teamless_profiles
        return context
