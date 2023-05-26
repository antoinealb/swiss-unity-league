# Generated by Django 4.1.7 on 2023-05-26 07:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("championship", "0013_eventplayerresult_championshi_event_i_f1cc30_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="Invoice",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(help_text="Start of the invoicing period"),
                ),
                ("end_date", models.DateField(help_text="End of invoicing period")),
                (
                    "event_organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="championship.eventorganizer",
                    ),
                ),
            ],
        ),
    ]
