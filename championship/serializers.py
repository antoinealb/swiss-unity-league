from championship.models import Event
from rest_framework import serializers


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["name", "date", "organizer", "format", "category"]

    organizer = serializers.CharField(source="organizer.name")
    format = serializers.CharField(source="get_format_display")
    category = serializers.CharField(source="get_category_display")
