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

# Generated by Django 5.0.4 on 2024-11-05 14:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("decklists", "0002_alter_decklist_mainboard_alter_decklist_sideboard"),
    ]

    operations = [
        migrations.AddField(
            model_name="collection",
            name="format_override",
            field=models.CharField(
                blank=True,
                choices=[
                    ("LIMITED", "Limited"),
                    ("MODERN", "Modern"),
                    ("LEGACY", "Legacy"),
                    ("PIONEER", "Pioneer"),
                    ("STANDARD", "Standard"),
                    ("EDH", "Commander/EDH"),
                    ("DC", "Duel Commander"),
                    ("PAUPER", "Pauper"),
                    ("OS", "Old School"),
                    ("PM", "Premodern"),
                    ("VINTAGE", "Vintage"),
                    ("MULTI", "Multi-Format"),
                ],
                help_text="Format of the decklist. If left empty, we will use the format of the event.",
                max_length=10,
                null=True,
                verbose_name="Format",
            ),
        ),
        migrations.AlterField(
            model_name="collection",
            name="name",
            field=models.CharField(
                blank=True,
                help_text="Name of the Decklist Collection. If left empty, we will show the name of the event.",
                max_length=128,
            ),
        ),
        migrations.RenameField(
            model_name="collection",
            old_name="name",
            new_name="name_override",
        ),
    ]
