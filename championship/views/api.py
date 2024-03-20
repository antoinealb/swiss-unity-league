import datetime

from django.db.models import Count
from django.http import Http404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    SAFE_METHODS,
    BasePermission,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from championship.models import Event, EventOrganizer
from championship.season import find_season_by_slug
from championship.serializers import EventInformationSerializer, EventSerializer


class FutureEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for the upcoming events page, showing future events."""

    serializer_class = EventSerializer

    def get_queryset(self):
        """Returns all Events in the future."""

        # This needs to be a function (get_queryset) instead of an attribute as
        # otherwise the today means "when the app was started.
        qs = Event.objects.filter(date__gte=datetime.date.today())
        qs = qs.select_related("organizer", "address", "organizer__default_address")
        return qs.order_by("date")


class PastEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for the upcoming events page, showing past events."""

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


class IsOwner(BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `organizer` attribute.
    """

    def has_object_permission(self, request, view, obj):
        return obj.organizer.user == request.user


class IsEventModificationAllowed(BasePermission):
    """
    Object-level permission check that verifies we are allowed by the SUL rules
    to still change an event.
    """

    def has_object_permission(self, request, view, obj: Event):
        if request.method in SAFE_METHODS:
            return True
        elif request.method in ["DELETE"]:
            return obj.can_be_deleted()

        return obj.can_be_edited()


class IsReadonly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True


class EventViewSet(viewsets.ModelViewSet):
    """API endpoint showing events and allowing their creation."""

    serializer_class = EventInformationSerializer
    queryset = Event.objects.all()
    permission_classes = [
        IsReadonly | (IsAuthenticated & IsOwner & IsEventModificationAllowed)
    ]

    @action(
        detail=False,
        name="List events needing results from me.",
        permission_classes=[IsAuthenticated],
    )
    def need_results(self, request):
        events = Event.objects.available_for_result_upload(request.user)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)
