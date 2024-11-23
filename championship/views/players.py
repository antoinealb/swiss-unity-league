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
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, TemplateView

from championship.forms import PlayerProfileForm
from championship.models import Event, Player, PlayerProfile, Result
from championship.score import get_results_with_qps
from championship.season import SEASONS_WITH_RANKING
from championship.views.base import PerSeasonMixin
from decklists.models import Decklist

LAST_RESULTS = "last_results"
TOP_FINISHES = "top_finishes"
QP_TABLE = "qp_table"
THEAD = "thead"
TBODY = "tbody"
TABLE = "table"
QPS = "QPs"
EVENTS = "Events"
PERFORMANCE_PER_FORMAT = "performance_per_format"


def add_to_table(table, column_title, row_title, value=1):
    """Increases the entry of the table in the given column-row pair by the value."""
    thead = table[THEAD]
    if column_title not in thead:
        return
    column_index = thead.index(column_title)
    tbody = table[TBODY]
    for existing_row in tbody:
        if existing_row[0] == row_title:
            existing_row[column_index] += value
            return
    new_row = [row_title] + [0] * (len(thead) - 1)
    new_row[column_index] = value
    tbody.append(new_row)


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


def sorted_most_accomplished_results(results):
    def accomplishments_sort_key(result_score):
        result, score = result_score
        if result.event.category == Event.Category.PREMIER:
            category = 1
        elif result.event.category == Event.Category.REGIONAL:
            category = 2
        elif result.event.category == Event.Category.REGULAR:
            category = 3
        else:
            category = 4

        return (
            category,
            result.single_elimination_result or 16 + result.ranking,
            -result.event.date.toordinal(),
        )

    return sorted(
        results,
        key=accomplishments_sort_key,
    )


class PlayerDetailsView(PerSeasonMixin, DetailView):
    season_view_name = "player_details_by_season"
    season_list = SEASONS_WITH_RANKING
    model = Player
    queryset = Player.objects.exclude(hidden_from_leaderboard=True)

    def get_template_names(self):
        return ["championship/player_details.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        results = get_results_with_qps(
            Result.objects.filter(
                player=context["player"],
                event__date__gte=self.current_season.start_date,
                event__date__lte=self.current_season.end_date,
            ).prefetch_related("event__organizer")
        )

        context[LAST_RESULTS] = sorted(
            results, key=lambda r: r[0].event.date, reverse=True
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

        qp_table = {
            THEAD: [
                "",
                Event.Category.PREMIER.label,
                Event.Category.REGIONAL.label,
                Event.Category.REGULAR.label,
                "Total",
            ],
            TBODY: [],
        }
        with_top_8_table = {
            THEAD: ["", Event.Category.PREMIER.label, Event.Category.REGIONAL.label],
            TBODY: [],
        }

        for result, score in sorted(context[LAST_RESULTS]):
            add_to_table(
                qp_table,
                column_title=result.event.get_category_display(),
                row_title=QPS,
                value=score.qps,
            )
            add_to_table(
                qp_table,
                column_title=result.event.get_category_display(),
                row_title=EVENTS,
            )
            if result.single_elimination_result:
                add_to_table(
                    with_top_8_table,
                    column_title=result.event.get_category_display(),
                    row_title=result.get_ranking_display(),
                )

        context[PERFORMANCE_PER_FORMAT] = self.performance_per_format(
            context[LAST_RESULTS]
        )

        if len(qp_table[TBODY]) > 0:
            # Compute the total and add it in the last column
            for row in qp_table[TBODY]:
                row[-1] = sum(row[1:])

            context[QP_TABLE] = qp_table

        context["top_finish_table"] = {
            "title": "Top 8 Finishes",
            TABLE: with_top_8_table,
        }

        context["decklists"] = self._decklists(context["player"])
        return context

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
            if result.single_elimination_result is None:
                return 0

            points = {
                Result.SingleEliminationResult.WINNER: 3,
                Result.SingleEliminationResult.FINALIST: 2,
                Result.SingleEliminationResult.SEMI_FINALIST: 1,
                Result.SingleEliminationResult.QUARTER_FINALIST: 0,
            }[result.single_elimination_result]

            # If we are in top4, it means we had one less match to win to get
            # to any rank. We can ignore QUARTER_FINALIST being 0, as they
            # would not be present in a top4 only match.
            if result.top_count == 4:
                points -= 1

            return points

        def extra_losses_for_top(result):
            ser = result.single_elimination_result
            if ser in (None, Result.SingleEliminationResult.WINNER):
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
