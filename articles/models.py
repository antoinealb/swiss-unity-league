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
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.validators import validate_image_file_extension
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from django_bleach.models import BleachField


class ArticleManager(models.Manager):
    def published(self):
        today = timezone.now().date()
        return self.filter(published_date__lte=today)

    def non_published(self):
        today = timezone.now().date()
        return self.exclude(published_date__lte=today)


def article_image_validator(image):
    if image.size > 0.5 * 1024 * 1024:
        raise ValidationError("Image file too large ( > 500KB )")


class Article(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    last_changed = models.DateTimeField(auto_now=True)
    published_date = models.DateField(
        null=True,
        blank=True,
        help_text="The date at which an article was published. Can be in the future for scheduled publishing.",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    content = BleachField(
        help_text="The article's content. Supports the following HTML tags: {}".format(
            ", ".join(settings.BLEACH_ALLOWED_TAGS_ARTICLE)
        ),
        blank=True,
        strip_tags=True,
        allowed_tags=settings.BLEACH_ALLOWED_TAGS_ARTICLE,
    )
    description = models.TextField(
        help_text="A short description that advertises the article. Used on the homepage and in meta data.",
        blank=True,
        max_length=200,
    )
    header_image = models.ImageField(
        upload_to="article_header",
        help_text="The advertisment image for the home page. Maximum size: 500KB. Supported formats: JPEG, PNG, WEBP.",
        blank=True,
        null=True,
        validators=[article_image_validator, validate_image_file_extension],
    )

    def __str__(self):
        return f"{self.title} (by {self.author})"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.published_date and self.published_date <= timezone.now().date():
            return reverse(
                "article-details",
                args=[
                    self.published_date.year,
                    self.published_date.month,
                    self.published_date.day,
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

    objects = ArticleManager()


@receiver(post_save, sender=Article)
def invalidate_article_cache(sender, instance, **kwargs):
    key = make_template_fragment_key("article_content", [instance.id])
    cache.delete(key)
