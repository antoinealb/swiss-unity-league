import math

from django.db import migrations, models


def estimate_rounds(match_point_list: list[int]) -> int:
    """Estimates the number of rounds based on a list of the match point.

    Copied from general parser functions so that future edits to this file
    don't change the results of this migration.
    """
    num_players = len(match_point_list)

    # The number of rounds needs to be at least the amount wins + draws of an individual player
    min_num_rounds = max([mp // 3 + mp % 3 for mp in match_point_list])

    # We add +1 because the actual rounds is likely to be 1 higher
    byes = min_num_rounds + 1 if num_players % 2 == 1 else 0

    total_wins = sum([mp // 3 for mp in match_point_list]) - byes
    total_losses = total_wins
    total_draws = sum([mp % 3 for mp in match_point_list])

    # We can estimate the number of rounds played based on the total number of wins, losses, draws and byes
    number_of_matches_per_player = (
        total_wins + total_draws + total_losses + byes
    ) / num_players

    # We round it up, since some players might drop out
    rounds_estimate = math.ceil(number_of_matches_per_player)

    return max(rounds_estimate, min_num_rounds)


def migrate_to_points(apps, schema_editor):
    EventPlayerResult = apps.get_model("championship", "EventPlayerResult")
    Event = apps.get_model("championship", "Event")
    db_alias = schema_editor.connection.alias

    for event in (
        Event.objects.using(db_alias)
        .annotate(num_results=models.Count("eventplayerresult"))
        .filter(num_results__gt=0)
    ):
        points = [
            e.points
            for e in EventPlayerResult.objects.using(db_alias).filter(event=event)
        ]
        rounds = estimate_rounds(points)

        for epr in EventPlayerResult.objects.using(db_alias).filter(event=event):
            if epr.win_count + epr.loss_count + epr.draw_count > 0:
                continue
            epr.win_count = epr.points // 3
            epr.draw_count = epr.points % 3
            epr.loss_count = rounds - epr.win_count - epr.draw_count
            epr.migrated_from_points_to_record = True
            epr.save()


def revert_migration(apps, schema_editor):
    EventPlayerResult = apps.get_model("championship", "EventPlayerResult")
    db_alias = schema_editor.connection.alias
    for epr in EventPlayerResult.objects.using(db_alias).filter(
        migrated_from_points_to_record=True
    ):
        epr.win_count = 0
        epr.loss_count = 0
        epr.draw_count = 0
        epr.save()


class Migration(migrations.Migration):
    dependencies = [
        ("championship", "0018_eventplayerresult_points_to_record"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventplayerresult",
            name="migrated_from_points_to_record",
            field=models.BooleanField(
                default=False,
                help_text="Indicates whether this result was automatically migrated from points to records. Used for diagnostics.",
            ),
        ),
        migrations.RunPython(migrate_to_points, revert_migration),
    ]
