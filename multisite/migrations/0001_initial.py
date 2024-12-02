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

from django.db import migrations

SITE_INSTANCES = [
    (1, "unityleague.ch", "Swiss Unity League"),
    (2, "playground-eu.unityleague.ch", "EU League (dev instance)"),
]


def create_initial_instances(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.all().delete()

    for id, domain, name in SITE_INSTANCES:
        Site.objects.create(id=id, domain=domain, name=name)


def delete_instances(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [migrations.RunPython(create_initial_instances, delete_instances)]
