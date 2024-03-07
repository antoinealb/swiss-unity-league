import datetime

from django.http import Http404
from rest_framework import viewsets
from rest_framework.response import Response

from championship.models import Event
from championship.season import find_season_by_slug
from championship.serializers import EventSerializer


class FutureEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """

    serializer_class = EventSerializer

    def get_queryset(self):
        """Returns all Events in the future."""

        # This needs to be a function (get_queryset) instead of an attribute as
        # otherwise the today means "when the app was started.
        qs = Event.objects.filter(date__gte=datetime.date.today())
        qs = qs.select_related("organizer", "address", "organizer__default_address")
        return qs.order_by("date")


class PastEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """

    serializer_class = EventSerializer

    def get_queryset(self):
        """Returns all Events in the past."""

        self.slug = self.kwargs.get("slug")
        try:
            self.current_season = find_season_by_slug(self.slug)
        except KeyError:
            raise Http404(f"Unknown season {self.slug}")

        # This needs to be a function (get_queryset) instead of an attribute as
        # otherwise the today means "when the app was started.
        qs = Event.objects.filter(date__lt=datetime.date.today())
        qs = qs.filter(
            date__gte=self.current_season.start_date,
            date__lte=self.current_season.end_date,
        )
        qs = qs.select_related("organizer", "address", "organizer__default_address")
        return qs.order_by("-date")


class ListFormats(viewsets.ViewSet):
    """API Endpoint returning all the formats we play in the league."""

    def list(self, request, format=None):
        return Response(sorted(Event.Format.labels))
