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
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from django_bleach.models import BleachField


class Article(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    last_changed = models.DateTimeField(auto_now=True)
    publication_time = models.DateField(
        null=True,
        blank=True,
        help_text="The date at which an article was published. Can be in the future for scheduled publishing.",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    content = BleachField(
        help_text="The article's content. Supports the following HTML tags: {}".format(
            ", ".join(settings.BLEACH_ALLOWED_TAGS)
        ),
        blank=True,
        strip_tags=True,
    )

    def __str__(self):
        return f"{self.title} (by {self.author})"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.publication_time and self.publication_time <= timezone.now().date():
            return reverse(
                "article-details",
                args=[
                    self.publication_time.year,
                    self.publication_time.month,
                    self.publication_time.day,
                    self.slug,
                ],
            )

        return reverse(
            "article-preview",
            args=[
                self.id,
                self.slug,
            ],
        )
