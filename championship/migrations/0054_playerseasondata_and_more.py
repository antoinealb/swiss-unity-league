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

# Generated by Django 5.0.4 on 2024-12-17 16:24

import django.db.models.deletion
from django.db import migrations, models

import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ("championship", "0053_alter_event_category_alter_organizerleague_category"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlayerSeasonData",
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
                    "season_slug",
                    models.CharField(
                        choices=[
                            ("eu2025", "Season 2025"),
                            ("eu2024mockup", "Mockup Season 2024"),
                        ],
                        max_length=50,
                    ),
                ),
                ("country", django_countries.fields.CountryField(max_length=2)),
                ("auto_assign_country", models.BooleanField(default=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="championship.player",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["player", "season_slug"], name="player_season_idx"
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="playerseasondata",
            constraint=models.UniqueConstraint(
                fields=("player", "season_slug"), name="unique_player_season"
            ),
        ),
    ]
