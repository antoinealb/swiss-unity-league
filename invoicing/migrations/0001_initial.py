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

# Generated by Django 4.1.7 on 2023-05-26 07:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("championship", "0013_eventplayerresult_championshi_event_i_f1cc30_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="Invoice",
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
                    "start_date",
                    models.DateField(help_text="Start of the invoicing period"),
                ),
                ("end_date", models.DateField(help_text="End of invoicing period")),
                (
                    "event_organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="championship.eventorganizer",
                    ),
                ),
            ],
        ),
    ]
