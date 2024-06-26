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
