from championship.models import Event
from rest_framework import serializers


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "name",
            "date",
            "organizer",
            "format",
            "address",
            "category",
            "details_url",
            "organizer_url",
        ]

    date = serializers.DateField(format="%a, %d.%m.%Y")
    organizer = serializers.CharField(source="organizer.name")
    format = serializers.CharField(source="get_format_display")
    address = serializers.SerializerMethodField()
    category = serializers.CharField(source="get_category_display")
    details_url = serializers.HyperlinkedIdentityField(view_name="event_details")
    organizer_url = serializers.HyperlinkedRelatedField(
        source="organizer", view_name="organizer_details", read_only=True
    )

    def get_address(self, event):
        if event.address:
            address = event.address
        # If there is no event address, try getting the organizer's default address
        elif event.organizer and event.organizer.default_address:
            address = event.organizer.default_address
        else:
            return ""

        return f", {address.short_string()}"
