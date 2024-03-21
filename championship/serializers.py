import datetime

from django.db import transaction
from django.templatetags.static import static
from rest_framework import serializers

from championship.models import (
    Address,
    Event,
    EventOrganizer,
    EventPlayerResult,
    Player,
    PlayerAlias,
)
from championship.views.results import clean_name


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "name",
            "date",
            "time",
            "startDateTime",
            "endDateTime",
            "organizer",
            "format",
            "locationName",
            "seoAddress",
            "shortAddress",
            "region",
            "category",
            "details_url",
            "organizer_url",
            "icon_url",
        ]

    date = serializers.DateField(format="%a, %d.%m.%Y")
    startDateTime = serializers.SerializerMethodField()
    endDateTime = serializers.SerializerMethodField()
    time = serializers.CharField(source="get_time_range_display")
    organizer = serializers.CharField(source="organizer.name")
    format = serializers.CharField(source="get_format_display")
    locationName = serializers.SerializerMethodField()
    seoAddress = serializers.SerializerMethodField()
    shortAddress = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    category = serializers.CharField(source="get_category_display")
    details_url = serializers.HyperlinkedIdentityField(view_name="event_details")
    organizer_url = serializers.HyperlinkedRelatedField(
        source="organizer", view_name="organizer_details", read_only=True
    )
    icon_url = serializers.SerializerMethodField()

    def get_address_helper(self, event) -> Address | None:
        if event.address:
            return event.address
        # If there is no event address, try getting the organizer's default address
        elif event.organizer and event.organizer.default_address:
            return event.organizer.default_address
        else:
            return None

    def get_region(self, event):
        address = self.get_address_helper(event)
        return address.get_region_display() if address else ""

    def get_seoAddress(self, event):
        address = self.get_address_helper(event)
        return address.get_seo_address() if address else ""

    def get_shortAddress(self, event):
        address = self.get_address_helper(event)
        return f", {address.short_string()}" if address else ""

    def get_locationName(self, event):
        address = self.get_address_helper(event)
        return address.location_name if address else ""

    def get_startDateTime(self, event):
        if event.start_time:
            start_datetime = datetime.datetime.combine(event.date, event.start_time)
        else:
            start_datetime = event.date
        return start_datetime.isoformat()

    def get_endDateTime(self, event):
        if event.end_time:
            end_datetime = datetime.datetime.combine(event.date, event.end_time)
            return end_datetime.isoformat()
        else:
            return ""

    def get_icon_url(self, event):
        return static(event.get_category_icon_url())


class EventPlayerResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventPlayerResult
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
            "decklists_url",
            "description",
            "organizer",
            "results",
        ]

    api_url = serializers.HyperlinkedIdentityField(view_name="events-detail")

    organizer = serializers.HyperlinkedRelatedField(
        view_name="organizers-detail", read_only=True
    )

    results = EventPlayerResultSerializer(
        many=True, source="eventplayerresult_set", read_only=False, required=False
    )

    def create(self, validated_data):
        # We need a custom create() because we want to attach informations from
        # the current user to the created event.
        validated_data.pop("eventplayerresult_set", [])
        organizer = EventOrganizer.objects.get(user=self.context["request"].user)
        addr = organizer.default_address
        # TODO: Support other addresses
        return Event.objects.create(
            organizer=organizer, address=organizer.default_address, **validated_data
        )

    @transaction.atomic
    def update(self, instance, validated_data):
        results = validated_data.pop("eventplayerresult_set", [])

        res = super().update(instance, validated_data)

        if results:
            instance.eventplayerresult_set.all().delete()

        for result in results:
            name = clean_name(result["player"]["name"])
            try:
                player = PlayerAlias.objects.get(name=name).true_player
            except PlayerAlias.DoesNotExist:
                player, _ = Player.objects.get_or_create(name=name)

            EventPlayerResult.objects.create(
                points=3 * result["win_count"] + result["draw_count"],
                player=player,
                event=instance,
                ranking=result["ranking"],
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


class PlayerAutocompleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = [
            "name",
        ]
