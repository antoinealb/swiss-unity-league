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

from django.db import transaction
from rest_framework import serializers

from championship.models import Event, EventOrganizer, Player, Result
from championship.tournament_valid import StandingsValidationError, validate_standings


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = [
            "player",
            "single_elimination_result",
            "ranking",
            "win_count",
            "loss_count",
            "draw_count",
        ]

    player = serializers.CharField(source="player.name")


class EventInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "api_url",
            "name",
            "date",
            "start_time",
            "end_time",
            "format",
            "category",
            "url",
            "description",
            "organizer",
            "results",
        ]

    api_url = serializers.HyperlinkedIdentityField(view_name="events-detail")

    organizer = serializers.HyperlinkedRelatedField(
        view_name="organizers-detail", read_only=True
    )

    results = ResultSerializer(
        many=True, source="result_set", read_only=False, required=False
    )

    def create(self, validated_data):
        # We need a custom create() because we want to attach informations from
        # the current user to the created event.
        validated_data.pop("result_set", [])
        organizer = EventOrganizer.objects.get(user=self.context["request"].user)
        # TODO: Support other addresses
        return Event.objects.create(
            organizer=organizer, address=organizer.default_address, **validated_data
        )

    @transaction.atomic
    def update(self, instance, validated_data):
        results = validated_data.pop("result_set", [])

        res = super().update(instance, validated_data)

        # If the results are not touched, there is nothing more to do
        if not results:
            return res

        # Check that uploaded results make sense
        results_for_validation = [
            (
                r["player"]["name"],
                r["win_count"] * 3 + r["draw_count"],
                (r["win_count"], r["draw_count"], r["loss_count"]),
            )
            for r in results
        ]
        try:
            validate_standings(results_for_validation, instance.category)
        except StandingsValidationError as e:
            error = {"message": e.ui_error_message()}
            if instance.results_validation_enabled:
                raise serializers.ValidationError(error)

        # Delete existing results to replace them with the new ones
        instance.result_set.all().delete()

        results.sort(key=lambda r: 3 * r["win_count"] + r["draw_count"], reverse=True)

        for i, result in enumerate(results):
            name = result["player"]["name"]
            player, created = Player.objects.get_or_create_by_name(name)

            Result.objects.create(
                points=3 * result["win_count"] + result["draw_count"],
                player=player,
                event=instance,
                ranking=i + 1,
                win_count=result["win_count"],
                loss_count=result["loss_count"],
                draw_count=result["draw_count"],
                single_elimination_result=result["single_elimination_result"],
            )

        return res


class OrganizerSerializer(serializers.ModelSerializer):
    events = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name="events-detail",
        source="event_set",
    )

    class Meta:
        model = EventOrganizer
        fields = ["id", "name", "events"]
