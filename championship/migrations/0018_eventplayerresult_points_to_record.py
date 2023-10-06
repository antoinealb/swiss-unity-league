from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("championship", "0017_event_results_validation_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventplayerresult",
            name="draw_count",
            field=models.PositiveIntegerField(
                default=0, help_text="Number of drawn matches"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="eventplayerresult",
            name="loss_count",
            field=models.PositiveIntegerField(
                default=0, help_text="Number of lost matches"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="eventplayerresult",
            name="win_count",
            field=models.PositiveIntegerField(
                default=0, help_text="Number of won matches"
            ),
            preserve_default=False,
        ),
    ]
