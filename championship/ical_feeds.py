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

from django_ical.views import ICalFeed

from championship.models import Event


class EventFeed(ICalFeed):
    """Calendar showing Premier & Regional events."""

    product_id = "-//example.com//Event//EN"
    timezone = "Europe/Zurich"

    def item_title(self, item):
        return f"[{item.organizer.name}] {item.name}"

    def item_description(self, item):
        return item.description

    def item_location(self, item):
        if item.address:
            return str(item.address)
        return None

    def item_start_datetime(self, item) -> datetime.datetime:
        if item.start_time:
            return datetime.datetime.combine(item.date, item.start_time)
        else:
            return item.date

    def item_end_datetime(self, item) -> datetime.datetime:
        if item.end_time:
            return datetime.datetime.combine(item.date, item.end_time)
        else:
            return item.date + datetime.timedelta(days=1)

    def items(self):
        return Event.objects.all().order_by("-date")


class AllEventsFeed(EventFeed):
    file_name = "allevents.ics"


class LargeEventFeed(EventFeed):
    file_name = "events.ics"

    def items(self):
        return (
            super()
            .items()
            .filter(category__in=(Event.Category.REGIONAL, Event.Category.PREMIER))
        )


class PremierEventsFeed(EventFeed):
    file_name = "premierevents.ics"

    def items(self):
        return super().items().filter(category=Event.Category.PREMIER)
