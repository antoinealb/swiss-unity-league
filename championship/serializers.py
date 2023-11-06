from championship.models import Event
from rest_framework import serializers
import datetime


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
            "address",
            "shortAddress",
            "region",
            "category",
            "details_url",
            "organizer_url",
        ]

    date = serializers.DateField(format="%a, %d.%m.%Y")
    startDateTime = serializers.SerializerMethodField()
    endDateTime = serializers.SerializerMethodField()
    time = serializers.CharField(source="get_time_range_display")
    organizer = serializers.CharField(source="organizer.name")
    format = serializers.CharField(source="get_format_display")
    address = serializers.SerializerMethodField()
    shortAddress = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    category = serializers.CharField(source="get_category_display")
    details_url = serializers.HyperlinkedIdentityField(view_name="event_details")
    organizer_url = serializers.HyperlinkedRelatedField(
        source="organizer", view_name="organizer_details", read_only=True
    )

    def get_address_helper(self, event):
        if event.address:
            return event.address
        # If there is no event address, try getting the organizer's default address
        elif event.organizer and event.organizer.default_address:
            return event.organizer.default_address

    def get_region(self, event):
        address = self.get_address_helper(event)
        return address.get_region_display() if address else ""

    def get_address(self, event):
        address = self.get_address_helper(event)
        return str(address) if address else ""

    def get_shortAddress(self, event):
        address = self.get_address_helper(event)
        return f", {address.short_string()}" if address else ""

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
