# Generated by Django 4.1.7 on 2023-06-25 08:55

from django.db import migrations, models
import django_bleach.models


class Migration(migrations.Migration):
    dependencies = [
        ("championship", "0015_player_email_alter_event_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventorganizer",
            name="description",
            field=django_bleach.models.BleachField(
                blank=True,
                help_text="Supports the following HTML tags: a, b, blockquote, em, i, li, ol, p, strong, ul",
            ),
        ),
        migrations.AlterField(
            model_name="eventorganizer",
            name="contact",
            field=models.EmailField(
                help_text="Prefered contact email (not visible to players)",
                max_length=254,
            ),
        ),
    ]
