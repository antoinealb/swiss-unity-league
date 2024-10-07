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

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView
from django.views.generic.dates import DateDetailView
from django.views.generic.edit import CreateView, UpdateView

from articles.forms import ArticleUpdateForm
from articles.models import Article


class ArticleView(DateDetailView):
    model = Article
    date_field = "publication_time"
    year_format = "%Y"
    month_format = "%m"
    day_format = "%d"


class ArticlePreviewView(DetailView):
    model = Article
    query_pk_and_slug = True


class ArticleUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "articles.change_article"
    model = Article
    query_pk_and_slug = True
    template_name = "articles/update_article.html"
    form_class = ArticleUpdateForm


class ArticleAddView(PermissionRequiredMixin, CreateView):
    permission_required = "articles.add_article"
    template_name = "articles/update_article.html"
    model = Article
    form_class = ArticleUpdateForm

    def form_valid(self, form: ArticleUpdateForm):
        # We assume the author is the person creating the article for the first
        # time. If it is ever needed to change this, it can be done through the
        # admin panel.
        form.instance.author = self.request.user
        return super().form_valid(form)
