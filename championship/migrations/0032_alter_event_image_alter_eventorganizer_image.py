# Generated by Django 4.2.9 on 2024-02-14 09:14

import championship.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("championship", "0031_eventorganizer_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Preferably in landscape orientation. Maximum size: 1.5MB. Supported formats: JPEG, PNG, WEBP.",
                null=True,
                upload_to="event",
                validators=[
                    championship.models.event_image_validator,
                    championship.models.image_type_validator,
                ],
            ),
        ),
        migrations.AlterField(
            model_name="eventorganizer",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Preferably in landscape orientation or squared. Maximum size: 500KB. Supported formats: JPEG, PNG, WEBP.",
                null=True,
                upload_to="organizer",
                validators=[
                    championship.models.organizer_image_validator,
                    championship.models.image_type_validator,
                ],
            ),
        ),
    ]