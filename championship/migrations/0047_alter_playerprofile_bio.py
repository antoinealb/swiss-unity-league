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

# Generated by Django 5.0.4 on 2024-11-16 08:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("championship", "0046_alter_playerprofile_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="playerprofile",
            name="bio",
            field=models.TextField(
                blank=True,
                help_text="Tell us about yourself: Magic background, favorite cards/formats/decks, tournament stories, other hobbies/interests, fun facts, jokes, ...",
                max_length=1000,
            ),
        ),
    ]
