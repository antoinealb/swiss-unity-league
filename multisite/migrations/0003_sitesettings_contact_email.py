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

# Generated by Django 5.0.4 on 2024-12-10 10:35

from django.db import migrations, models


def create_initial_instances(apps, schema_editor):
    emails = {
        "unityleague.ch": "leoninleague@gmail.com",
        "playground-eu.unityleague.ch": "nocontact@example.com",
    }
    SiteSettings = apps.get_model("multisite", "SiteSettings")

    for site_settings in SiteSettings.objects.all():
        email = emails[site_settings.site.domain]
        site_settings.contact_email = email
        site_settings.save()


class Migration(migrations.Migration):

    dependencies = [
        ("multisite", "0002_initial"),
    ]

    operations = [
        # 1. Add the field allowing empty values
        migrations.AddField(
            model_name="sitesettings",
            name="contact_email",
            field=models.EmailField(
                blank=True, max_length=254, verbose_name="Contact email"
            ),
        ),
        # 2. backfill the value
        migrations.RunPython(create_initial_instances, migrations.RunPython.noop),
        # 3. mark it as required after backfill. This will fail if one
        # instance was forgotten.
        migrations.AlterField(
            model_name="sitesettings",
            name="contact_email",
            field=models.EmailField(max_length=254, verbose_name="Contact email"),
        ),
    ]