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

# Generated by Django 4.2.9 on 2024-02-13 16:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("championship", "0030_event_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventorganizer",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="An image to represent the organizer. Will be shown on the organizer details page.",
                null=True,
                upload_to="organizer",
            ),
        ),
    ]
