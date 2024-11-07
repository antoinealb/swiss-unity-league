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

from articles.views import (
    ArticleAddView,
    ArticleArchiveView,
    ArticleAttachmentCreateView,
    ArticleDraftView,
    ArticlePreviewView,
    ArticleUpdateView,
    ArticleView,
)

urlpatterns = [
    path("", ArticleArchiveView.as_view(), name="article-list"),
    path(
        "<int:year>/<int:month>/<int:day>/<slug:slug>/",
        ArticleView.as_view(),
        name="article-details",
    ),
    path(
        "preview/<int:pk>/<slug:slug>/",
        ArticlePreviewView.as_view(),
        name="article-preview",
    ),
    path(
        "edit/<int:pk>/<slug:slug>/",
        ArticleUpdateView.as_view(),
        name="article-update",
    ),
    path(
        "create/",
        ArticleAddView.as_view(),
        name="article-create",
    ),
    path(
        "drafts/",
        ArticleDraftView.as_view(),
        name="article-drafts",
    ),
    path(
        "attachment/",
        ArticleAttachmentCreateView.as_view(),
        name="article-attachment-create",
    ),
]
