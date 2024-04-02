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

# Generated by Django 4.2.1 on 2023-05-31 14:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoicing", "0003_invoice_payment_received_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="discount",
            field=models.IntegerField(default=0, help_text="Flat discount in CHF"),
        ),
        migrations.AddField(
            model_name="invoice",
            name="notes",
            field=models.TextField(
                blank=True,
                help_text="Notes about this invoice, only visible by Unity League staff.",
            ),
        ),
    ]
