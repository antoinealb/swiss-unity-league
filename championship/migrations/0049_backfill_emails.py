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

# Generated by Django 5.0.4 on 2024-12-01 17:54

from django.db import migrations


def backfill_email(apps, schema_editor):
    EventOrganizer = apps.get_model("championship", "EventOrganizer")

    for eo in EventOrganizer.objects.filter(user__email="").exclude(contact=""):
        eo.user.email = eo.contact
        eo.user.save()


class Migration(migrations.Migration):

    dependencies = [
        ("championship", "0048_rename_single_elimination_result_result_playoff_result"),
    ]

    operations = [migrations.RunPython(backfill_email, migrations.RunPython.noop)]