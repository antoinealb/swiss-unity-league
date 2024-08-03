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

# Generated by Django 5.0.6 on 2024-07-26 10:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("championship", "0041_organizerleague"),
    ]

    operations = [
        migrations.RenameModel("EventPlayerResult", "Result"),
        migrations.RenameIndex(
            model_name="result",
            new_name="championship_result_event_idx",
            old_name="championshi_event_i_f1cc30_idx",
        ),
    ]