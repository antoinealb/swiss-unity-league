# Generated by Django 4.1.1 on 2023-01-14 13:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("championship", "0007_alter_event_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="hidden_from_leaderboard",
            field=models.BooleanField(
                default=False,
                help_text="If true, this should be hidden from the global leaderboard. Useful for virtual players, such as Eventlink's REDACTED.",
            ),
        ),
    ]