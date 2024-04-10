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

from django.urls import path

from . import views

urlpatterns = [
    path("<uuid:pk>/", views.DecklistView.as_view(), name="decklist-details"),
    path("<uuid:pk>/edit/", views.DecklistUpdateView.as_view(), name="decklist-update"),
    path(
        "collections/<int:pk>/",
        views.CollectionView.as_view(),
        name="collection-details",
    ),
]
