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

# Generated by Django 5.0.4 on 2024-11-07 17:13

import django.core.validators
from django.db import migrations, models

import articles.models


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0002_alter_article_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="description",
            field=models.TextField(
                blank=True,
                help_text="A short description that advertises the article. Used on the homepage and in meta data.",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="header_image",
            field=models.ImageField(
                blank=True,
                help_text="The advertisment image for the home page. Maximum size: 500KB. Supported formats: JPEG, PNG, WEBP.",
                null=True,
                upload_to="article_header",
                validators=[
                    articles.models.article_image_validator,
                    django.core.validators.validate_image_file_extension,
                ],
            ),
        ),
    ]
