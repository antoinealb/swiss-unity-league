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
            "region",
            "category",
            "details_url",
            "organizer_url",
        ]

    date = serializers.DateField(format="%d.%m.%Y")
    organizer = serializers.CharField(source="organizer.name")
    format = serializers.CharField(source="get_format_display")
    region = serializers.SerializerMethodField()
    category = serializers.CharField(source="get_category_display")
    details_url = serializers.HyperlinkedIdentityField(view_name="event_details")
    organizer_url = serializers.HyperlinkedRelatedField(
        source="organizer", view_name="organizer_details", read_only=True
    )

    def get_region(self, obj):
        # Try getting the region from the event's address
        if obj.address:
            region = obj.address.get_region_display()
        # If there is no address, try getting the region from the organizer's default address
        elif obj.organizer and obj.organizer.default_address:
            region = obj.organizer.default_address.get_region_display()
        else:
            region = ""

        return region
