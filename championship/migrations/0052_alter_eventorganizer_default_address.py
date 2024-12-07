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

# Generated by Django 5.0.4 on 2024-12-07 15:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("championship", "0051_alter_address_country"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eventorganizer",
            name="default_address",
            field=models.ForeignKey(
                help_text="The location of your store or the location where most of your events take place.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="championship.address",
                verbose_name="Main location",
            ),
        ),
    ]
