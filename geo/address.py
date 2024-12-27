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

from collections import ChainMap

from django.conf import settings
from django.utils.module_loading import import_string

from geopy.exc import GeocoderServiceError
from geopy.geocoders.base import Geocoder
from prometheus_client import Histogram
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_delay,
    wait_exponential_jitter,
)

from championship.models import Address

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


@geocode_duration.time()
@retry(
    stop=stop_after_delay(5),
    wait=wait_exponential_jitter(initial=0.05, max=2),
    retry=retry_if_exception_type(GeocoderServiceError),
    reraise=True,
)
def address_to_coordinate(addr: Address) -> tuple[float, float]:
    coder = _make_geocoder()
    address_parts = [
        addr.street_address,
        f"{addr.postal_code} {addr.city}",
        addr.country.name,
    ]
    location = coder.geocode(", ".join(address_parts))
    return location.latitude, location.longitude
