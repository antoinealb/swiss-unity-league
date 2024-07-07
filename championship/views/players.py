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

from django.shortcuts import get_object_or_404
from django.views.generic import DetailView

from championship.models import Event, EventPlayerResult, Player
from championship.score import get_results_with_qps
from championship.season import SEASONS_WITH_RANKING
from championship.views.base import PerSeasonMixin

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
            EventPlayerResult.objects.filter(
                player=context["player"],
                event__date__gte=self.current_season.start_date,
                event__date__lte=self.current_season.end_date,
            )
        )

        context[LAST_RESULTS] = sorted(
            results, key=lambda r: r[0].event.date, reverse=True
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
        without_top_8_table = {
            THEAD: ["", Event.Category.REGIONAL.label, Event.Category.REGULAR.label],
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

            if result.has_top8:
                # For events with top 8 only display the results if the player made top 8
                if result.single_elimination_result:
                    add_to_table(
                        with_top_8_table,
                        column_title=result.event.get_category_display(),
                        row_title=result.get_ranking_display(),
                    )
            else:
                # For swiss rounds only display top 3 finishes
                if result.ranking < 4:
                    add_to_table(
                        without_top_8_table,
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

        context[TOP_FINISHES] = [
            {"title": "Top 8 Finishes", TABLE: with_top_8_table},
            {"title": "Best Swiss Round Finishes", TABLE: without_top_8_table},
        ]
        return context

    def performance_per_format(self, results) -> dict[str, Performance]:
        """Returns the peformance per format, with the display name of the format as key."""

        def extra_wins_for_top(result):
            if result.single_elimination_result is None:
                return 0

            points = {
                EventPlayerResult.SingleEliminationResult.WINNER: 3,
                EventPlayerResult.SingleEliminationResult.FINALIST: 2,
                EventPlayerResult.SingleEliminationResult.SEMI_FINALIST: 1,
                EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST: 0,
            }[result.single_elimination_result]

            # If we are in top4, it means we had one less match to win to get
            # to any rank. We can ignore QUARTER_FINALIST being 0, as they
            # would not be present in a top4 only match.
            if result.top_count == 4:
                points -= 1

            return points

        def extra_losses_for_top(result):
            ser = result.single_elimination_result
            if ser in (None, EventPlayerResult.SingleEliminationResult.WINNER):
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

        return perf_per_format
