# Generated by Django 4.1.7 on 2023-06-30 21:52

from django.db import migrations, models
import django.db.models.deletion
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
        migrations.CreateModel(
            name="Address",
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
                ("location_name", models.CharField(max_length=255)),
                ("street_address", models.CharField(max_length=255)),
                ("city", models.CharField(max_length=255)),
                ("postal_code", models.CharField(max_length=10)),
                (
                    "region",
                    models.CharField(
                        choices=[
                            ("AG", "Aargau"),
                            ("AR", "Appenzell Ausserrhoden"),
                            ("AI", "Appenzell Innerrhoden"),
                            ("BL", "Basel-Landschaft"),
                            ("BS", "Basel-Stadt"),
                            ("BE", "Bern"),
                            ("FR", "Fribourg"),
                            ("GE", "Genève"),
                            ("GL", "Glarus"),
                            ("GR", "Graubünden"),
                            ("JU", "Jura"),
                            ("LU", "Luzern"),
                            ("NE", "Neuchâtel"),
                            ("NW", "Nidwalden"),
                            ("OW", "Obwalden"),
                            ("SH", "Schaffhausen"),
                            ("SZ", "Schwyz"),
                            ("SO", "Solothurn"),
                            ("SG", "Sankt Gallen"),
                            ("TG", "Thurgau"),
                            ("TI", "Ticino"),
                            ("UR", "Uri"),
                            ("VS", "Valais"),
                            ("VD", "Vaud"),
                            ("ZG", "Zug"),
                            ("ZH", "Zürich"),
                            ("FR_DE", "Freiburg im Breisgau (DE)"),
                        ],
                        default="ZH",
                        max_length=5,
                    ),
                ),
                (
                    "country",
                    models.CharField(
                        choices=[
                            ("CH", "Switzerland"),
                            ("AT", "Austria"),
                            ("DE", "Germany"),
                            ("IT", "Italy"),
                            ("LI", "Liechtenstein"),
                            ("FR", "France"),
                        ],
                        default="CH",
                        max_length=2,
                    ),
                ),
                (
                    "organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="addresses",
                        to="championship.eventorganizer",
                    ),
                ),
            ],
        ),
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
        migrations.AddField(
            model_name="eventorganizer",
            name="default_address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="championship.address",
            ),
        ),
    ]
