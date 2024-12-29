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

import hashlib
from collections import ChainMap
from datetime import timedelta

from django.conf import settings
from django.utils.module_loading import import_string

from geopy.exc import GeocoderServiceError
from geopy.geocoders.base import Geocoder, Point
from prometheus_client import Histogram
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_delay,
    wait_exponential_jitter,
)

from championship.cache_function import cache_function

geocode_duration = Histogram(
    "geocode_latency_seconds", "Duration of a call to the geocoding backend"
)


GEOCODER_DEFAULT = {
    "BACKEND": "geopy.geocoders.Nominatim",
    "USER_AGENT": "unityleague.gg",
    "KWARGS": {},
}


def _make_geocoder() -> Geocoder:
    geocoder = getattr(settings, "GEO_GEOCODER", {})
    geocoder = ChainMap(geocoder, GEOCODER_DEFAULT)
    kwargs = geocoder["KWARGS"]
    user_agent = geocoder["USER_AGENT"]
    GeocoderClass = import_string(geocoder["BACKEND"])
    return GeocoderClass(user_agent=user_agent, timeout=2, **kwargs)


@cache_function(
    # We use a digest to remove non-ascii characters
    cache_key=lambda s: hashlib.md5(s.encode()).hexdigest(),
    # Geocoding results are expensive and unlikely to change, keep them for
    # long.
    cache_ttl=timedelta(days=31).total_seconds(),
)
@geocode_duration.time()  # measure geocoding latency, including retries
@retry(
    stop=stop_after_delay(5),
    wait=wait_exponential_jitter(initial=0.05, max=2),
    retry=retry_if_exception_type(GeocoderServiceError),
    reraise=True,
)
def _geocoder_query_cached(addr: str) -> Point | None:
    coder = _make_geocoder()
    return coder.geocode(addr)


def address_to_coordinate(addr) -> tuple[float, float]:
    address_parts = [
        addr.street_address,
        f"{addr.postal_code} {addr.city}",
        addr.country.name,
    ]

    location = _geocoder_query_cached(", ".join(address_parts))
    return location.latitude, location.longitude
