from championship.models import Event
from rest_framework import serializers
from rest_framework.reverse import reverse


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["name", "date", "organizer", "format", "category", "details_url"]

    organizer = serializers.CharField(source="organizer.name")
    format = serializers.CharField(source="get_format_display")
    category = serializers.CharField(source="get_category_display")
    details_url = serializers.HyperlinkedIdentityField(view_name="event_details")
