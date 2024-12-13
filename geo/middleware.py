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

import dataclasses
import logging

from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.http.request import HttpRequest

from geoip2.errors import AddressNotFoundError
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)
del logging  # avoids accidental use

geoip_lookups_count = Counter(
    "geoip_lookups_total", "Number of GeoIP lookups performed, by status", ["status"]
)

geoip_lookup_duration = Histogram(
    "geoip_lookup_duration_seconds", "Duration of the GeoIP database lookup"
)


@dataclasses.dataclass
class GeoIPData:
    city: str
    country_code: str
    latitude: float
    longitude: float


def _get_ip(request):
    try:
        forwarded_for = request.META["HTTP_X_FORWARDED_FOR"]
        return forwarded_for.split(",")[0]
    except KeyError:
        return request.META["REMOTE_ADDR"]


class GeoIpMiddleware:
    def __init__(self, get_response, geoip=None):
        self.get_response = get_response
        if geoip:
            self.geoip = geoip
        else:
            try:
                self.geoip = GeoIP2()
            except GeoIP2Exception:
                self.geoip = None
                logger.warning(
                    "Could not open GeoIP database, maybe run 'manage.py download_ipdb' ?"
                )

    @geoip_lookup_duration.time()
    def geoip_lookup(self, ip_addr: str) -> GeoIPData | None:
        # If we could not read the database, abort
        if not self.geoip:
            return None

        try:
            data = self.geoip.city(ip_addr)
        except AddressNotFoundError:
            geoip_lookups_count.labels("not_found").inc()
            return None

        geoip_lookups_count.labels("found").inc()
        return GeoIPData(
            city=data["city"],
            country_code=data["country_code"],
            latitude=data["latitude"],
            longitude=data["longitude"],
        )

    def __call__(self, request: HttpRequest):
        request.geoip_data = self.geoip_lookup(_get_ip(request))
        response = self.get_response(request)

        return response
