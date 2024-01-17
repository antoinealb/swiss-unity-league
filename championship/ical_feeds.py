import datetime
from django_ical.views import ICalFeed
from championship.models import Event


class LargeEventFeed(ICalFeed):
    """Calendar showing Premier & Regional events."""

    product_id = "-//example.com//Event//EN"
    timezone = "Europe/Zurich"
    file_name = "events.ics"

    def items(self):
        return Event.objects.all().order_by("-date")

    def item_title(self, item):
        return f"[{item.organizer.name}] {item.name}"

    def item_description(self, item):
        return item.description

    def item_start_datetime(self, item) -> datetime.datetime:
        if item.start_time:
            return item.date + item.start_time
        else:
            return item.date

    def item_end_datetime(self, item) -> datetime.datetime:
        if item.end_time:
            return item.date + item.end_time
        else:
            return item.date + datetime.timedelta(days=1)
