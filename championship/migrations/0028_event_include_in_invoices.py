# Generated by Django 4.2.9 on 2024-02-09 15:12

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("championship", "0027_alter_eventplayerresult_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="include_in_invoices",
            field=models.BooleanField(
                default=True, help_text="Whether this event will be in invoices."
            ),
        ),
    ]
