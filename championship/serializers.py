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

import datetime

from django.templatetags.static import static
from rest_framework import serializers

from championship.models import Address, Event


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
