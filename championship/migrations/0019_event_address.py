# Generated by Django 4.1.7 on 2023-06-26 20:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("championship", "0018_alter_eventorganizer_addresses_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="championship.address",
            ),
        ),
    ]
