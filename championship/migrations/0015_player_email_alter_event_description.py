# Generated by Django 4.1.7 on 2023-06-29 20:05

from django.db import migrations, models
import django_bleach.models


class Migration(migrations.Migration):
    dependencies = [
        ("championship", "0014_alter_eventorganizer_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name="event",
            name="description",
            field=django_bleach.models.BleachField(
                blank=True,
                help_text="Supports the following HTML tags: a, b, blockquote, em, i, li, ol, p, strong, ul",
            ),
        ),
    ]
