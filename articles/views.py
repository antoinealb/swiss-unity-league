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


from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import reverse
from django.views.generic import DetailView, ListView
from django.views.generic.dates import ArchiveIndexView, DateDetailView
from django.views.generic.edit import CreateView, FormView, UpdateView

from articles.forms import ArticleUpdateForm, AttachmentUploadForm
from articles.models import Article
from file_storage_db.models import File


class ArticleArchiveView(ArchiveIndexView):
    model = Article
    date_field = "published_date"
    context_object_name = "articles"


class ArticleView(DateDetailView):
    model = Article
    date_field = "published_date"
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


class ArticleDraftView(PermissionRequiredMixin, ListView):
    permission_required = "articles.add_article"
    model = Article
    template_name = "articles/article_draft.html"
    context_object_name = "articles"
    ordering = "-last_changed"

    def get_queryset(self):
        return Article.objects.non_published().filter(author=self.request.user)


class ArticleAttachmentCreateView(
    PermissionRequiredMixin, SuccessMessageMixin, FormView
):
    permission_required = "articles.add_article"
    form_class = AttachmentUploadForm
    template_name = "articles/upload_attachment.html"

    def form_valid(self, form):
        file = form.cleaned_data["file"]
        path = f"articles/{file.name}"

        # In-DB storage does not support writing for now
        # TODO: Unique filename
        # TODO: Use Django's Storage API here
        self.db_file, _ = File.objects.get_or_create(filename=path)
        self.db_file.content = b"".join(file.chunks())
        self.db_file.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("article-attachment-create")

    def get_success_message(self, cleaned_data):
        url = self.request.build_absolute_uri(
            f"/{settings.MEDIA_URL}/f{self.db_file.filename}"
        )
        return f"Your file is now available at {url}"
