# Copyright 2025 Leonin League
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

import datetime

from championship.models import Event
from championship.score.season_2025 import ScoreMethod2025
from championship.score.types import LeaderboardScore, QualificationType
from championship.season import INVITATIONAL_SPRING_2025


class ScoreMethodInvitationalSpring2025(ScoreMethod2025):
    LEADERBOARD_QUALIFICATION_RANK = 80
    DIRECT_QUALIFICATION_REASON = (
        "Direct qualification for {ranking} place at '{event_name}'"
    )
    SEASON = INVITATIONAL_SPRING_2025

    @classmethod
    def finalize_scores(
        cls,
        scores_by_player: dict[int, ScoreMethod2025.Score],
    ) -> dict[int, LeaderboardScore]:
        """Implements the last step of score processing.

        This function takes a dictionary of player_id to Score mappings and turns it
        into a dictionary of player_id to LeaderboardScore mappings, checking the maximum number of byes
        and deciding who is qualified and not.

        Returns a dictionary of player_id to LeaderboardScore.

        """
        events = (
            Event.objects.filter(
                category__in=[Event.Category.PREMIER, Event.Category.REGIONAL],
                date__gte=cls.SEASON.start_date,
                date__lte=cls.SEASON.end_date,
            )
            .prefetch_related("result_set")
            .order_by("date")
        )
        direct_qualification_reasons_by_player = {}
        for event in events:
            has_tops = event.result_set.filter(playoff_result__isnull=False).exists()
            if not has_tops:
                qualifications = 0
            elif event.category == Event.Category.PREMIER:
                qualifications = 2
            else:
                qualifications = 1
            for result in sorted(event.result_set.all()):
                if (
                    result.player_id not in direct_qualification_reasons_by_player
                    and qualifications
                ):
                    direct_qualification_reasons_by_player[result.player_id] = (
                        cls.DIRECT_QUALIFICATION_REASON.format(
                            ranking=result.get_ranking_display(),
                            event_name=event.name,
                        )
                    )
                    qualifications -= 1
                    if qualifications == 0:
                        break

        if cls.SEASON.can_enter_results(datetime.date.today()):
            leaderboard_reason = "At the end of the season this place qualifies for the SUL Invitational Spring 2025"
        else:
            leaderboard_reason = "Qualified for the SUL Invitational Spring 2025"

        sorted_scores = sorted(
            scores_by_player.items(), key=lambda x: x[1].qps, reverse=True
        )
        scores = {}
        for i, (player_id, score) in enumerate(sorted_scores):
            rank = i + 1

            scores[player_id] = LeaderboardScore(
                total_score=score.qps,
                rank=rank,
            )
            if player_id in direct_qualification_reasons_by_player:
                scores[player_id].qualification_type = QualificationType.DIRECT
                scores[player_id].qualification_reason = (
                    direct_qualification_reasons_by_player[player_id]
                )
            elif rank <= cls.LEADERBOARD_QUALIFICATION_RANK:
                scores[player_id].qualification_type = QualificationType.LEADERBOARD
                scores[player_id].qualification_reason = leaderboard_reason

        return scores
