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

from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from api import views

api_router = routers.DefaultRouter()
api_router.register(r"events", views.EventViewSet, basename="events")
api_router.register(r"formats", views.ListFormats, basename="formats")
api_router.register(r"organizers", views.OrganizersViewSet, basename="organizers")

urlpatterns = [
    path("", include(api_router.urls)),
    path("auth/", obtain_auth_token, name="api_auth_token"),
]
