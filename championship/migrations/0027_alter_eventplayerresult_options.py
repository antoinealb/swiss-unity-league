# Generated by Django 4.2.9 on 2024-02-02 15:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("championship", "0026_event_edit_deadline_override"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="eventplayerresult",
            options={"verbose_name": "Result"},
        ),
    ]
