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

# Generated by Django 4.1.3 on 2022-12-04 20:34

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="The name of the event as defined by the organizer",
                        max_length=200,
                    ),
                ),
                (
                    "date",
                    models.DateField(
                        help_text="The date of the event. For multi-days event, pick the first day."
                    ),
                ),
                (
                    "url",
                    models.URLField(
                        help_text="A website for information, ticket sale, etc."
                    ),
                ),
                (
                    "format",
                    models.CharField(
                        choices=[
                            ("LEGACY", "Legacy"),
                            ("MODERN", "Modern"),
                            ("LIMITED", "Limited"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("REGULAR", "SUL Regular"),
                            ("REGIONAL", "SUL Regional"),
                            ("PREMIER", "SUL Premier"),
                        ],
                        max_length=10,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EventPlayerResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "points",
                    models.IntegerField(
                        help_text="Number of points scored by that player"
                    ),
                ),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="championship.event",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Player",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                (
                    "events",
                    models.ManyToManyField(
                        through="championship.EventPlayerResult",
                        to="championship.event",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="eventplayerresult",
            name="player",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="championship.player"
            ),
        ),
        migrations.CreateModel(
            name="EventOrganizer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                (
                    "contact",
                    models.EmailField(
                        help_text="Prefered contact email", max_length=254
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="event",
            name="organizer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="championship.eventorganizer",
            ),
        ),
    ]
