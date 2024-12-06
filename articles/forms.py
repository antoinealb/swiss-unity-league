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

from django import forms
from django.conf import settings

from tinymce.widgets import TinyMCE

from articles.models import Article
from championship.forms import SubmitButtonMixin


class ArticleUpdateForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = [
            "title",
            "content",
            "published_date",
            "header_image",
            "description",
        ]
        widgets = {
            "published_date": forms.DateInput(attrs={"type": "date"}),
            "content": TinyMCE(
                mce_attrs={
                    "toolbar": "undo redo | h2 h3 h4 | bold italic | link unlink | bullist numlist",
                    "link_assume_external_targets": "http",
                },
            ),
        }
        help_texts = {
            "content": """Supports the following HTML tags: {}.
To reference a card wrap it in brackets (e.g. [[Daze]]). To reference a decklist just paste a unityleague link.""".format(
                ", ".join(settings.BLEACH_ALLOWED_TAGS_ARTICLE)
            ),
        }


class AttachmentUploadForm(forms.Form, SubmitButtonMixin):
    file = forms.FileField(required=True, help_text="The file to upload.")
