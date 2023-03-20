# Generated by Django 4.1.7 on 2023-03-20 15:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("championship", "0010_event_decklists_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlayerAlias",
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
                ("name", models.CharField(max_length=200)),
                (
                    "true_player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="championship.player",
                    ),
                ),
            ],
        ),
    ]