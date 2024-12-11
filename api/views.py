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

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response

from api.serializers import EventInformationSerializer, OrganizerSerializer
from championship.models import Event, EventOrganizer


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
    queryset = Event.objects.all().prefetch_related("result_set", "result_set__player")
    permission_classes = [
        IsReadonly | (IsAuthenticated & IsOwner & IsEventModificationAllowed)
    ]

    def perform_create(self, serializer):
        category = serializer.validated_data["category"]
        if Event.Category.requires_permission(category):
            raise ValidationError(
                f"Please contact us to create an event of category {category}."
            )
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        instance = self.get_object()
        old_category = instance.category
        new_category = serializer.validated_data.get("category", old_category)
        if old_category != new_category:
            if Event.Category.requires_permission(new_category):
                raise ValidationError(
                    f"Please contact us to change the category to {new_category}."
                )
            if Event.Category.requires_permission(old_category):
                raise ValidationError(
                    f"Please contact us to change the category of {old_category} events."
                )
        return super().perform_update(serializer)

    @action(
        detail=False,
        name="List events needing results from me.",
        permission_classes=[IsAuthenticated],
    )
    def need_results(self, request):
        events = Event.objects.available_for_result_upload(request.user)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)


class OrganizersViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrganizerSerializer
    queryset = EventOrganizer.objects.all().prefetch_related("event_set")

    @action(
        detail=False,
        name="Link to organizer profile for the logged in organizer.",
        permission_classes=[IsAuthenticated],
        methods=["get"],
    )
    def me(self, request):
        organizer = EventOrganizer.objects.get(user=request.user)
        serializer = self.get_serializer(organizer)
        return Response(serializer.data)
