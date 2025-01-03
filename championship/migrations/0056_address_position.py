# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Generated by Django 5.0.4 on 2024-12-27 13:08
import logging
from collections import ChainMap

import django.contrib.gis.db.models.fields
from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import migrations
from django.utils.module_loading import import_string

from geopy.exc import GeocoderServiceError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_delay,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

del logging

GEOCODER_DEFAULT = {
    "BACKEND": "geopy.geocoders.Nominatim",
    "USER_AGENT": "unityleague.gg",
    "KWARGS": {},
}


def _make_geocoder():
    geocoder = getattr(settings, "GEO_GEOCODER", {})
    geocoder = ChainMap(geocoder, GEOCODER_DEFAULT)
    kwargs = geocoder["KWARGS"]
    user_agent = geocoder["USER_AGENT"]
    GeocoderClass = import_string(geocoder["BACKEND"])
    return GeocoderClass(user_agent=user_agent, timeout=2, **kwargs)


@retry(
    stop=stop_after_delay(30),
    wait=wait_exponential_jitter(initial=0.05, max=2),
    retry=retry_if_exception_type(GeocoderServiceError),
    reraise=True,
)
def address_to_coordinate(addr) -> tuple[float, float] | None:
    coder = _make_geocoder()
    address_parts = [
        addr.street_address,
        f"{addr.postal_code} {addr.city}",
        addr.country.name,
    ]
    location = coder.geocode(", ".join(address_parts))
    if location is None:
        return None
    return location.latitude, location.longitude


def backfill_position(apps, schema_editor):
    Address = apps.get_model("championship", "Address")

    for addr in Address.objects.all():
        coord = address_to_coordinate(addr)
        if coord is None:
            logger.error("Could not find coordinates for %s", addr.location_name)
            continue
        addr.position = Point(*coord)
        addr.save()


class Migration(migrations.Migration):

    dependencies = [
        ("championship", "0055_nationalleaderboard_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="address",
            name="position",
            field=django.contrib.gis.db.models.fields.PointField(
                help_text="The position of the venue on a map. Usually inferred from the address",
                srid=4326,
                default=Point(0, 0),
            ),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_position, migrations.RunPython.noop),
    ]
