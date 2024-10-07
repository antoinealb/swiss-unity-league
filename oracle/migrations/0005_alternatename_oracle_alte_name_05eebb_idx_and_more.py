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

# Generated by Django 5.0.4 on 2024-10-03 07:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("oracle", "0004_card_image_uri"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="alternatename",
            index=models.Index(fields=["name"], name="oracle_alte_name_05eebb_idx"),
        ),
        migrations.AddIndex(
            model_name="card",
            index=models.Index(fields=["name"], name="oracle_card_name_6186dc_idx"),
        ),
    ]
