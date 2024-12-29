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

from unittest.mock import Mock

from django.test import TestCase, override_settings

from geopy.exc import GeocoderQuotaExceeded
from geopy.point import Point

from championship.models import Address
from geo.address import address_to_coordinate

MockGeocoder = Mock()


@override_settings(
    GEO_GEOCODER={"BACKEND": "geo.tests.test_geocoding_address.MockGeocoder"}
)
class GeoCodingTestCase(TestCase):
    def setUp(self):
        self.geocoder = Mock()
        MockGeocoder.return_value = self.geocoder

        self.address = Address(
            location_name="Test Location",
            street_address="Brandschenkestrasse 110",
            city="Zürich",
            postal_code="8002",
            country="CH",
        )
        self.want_coordinates = (47.3656492, 8.5248522)
        self.geocoder.geocode.return_value = Point(self.want_coordinates)

    def test_hardcoded_address(self):
        coord = address_to_coordinate(self.address)
        self.geocoder.geocode.assert_any_call(
            "Brandschenkestrasse 110, 8002 Zürich, Switzerland"
        )
        self.assertEqual(coord, (47.3656492, 8.5248522))

    def test_retry_policy(self):
        self.geocoder.geocode.side_effect = [
            GeocoderQuotaExceeded,
            Point(self.want_coordinates),
        ]
        coord = address_to_coordinate(self.address)
        self.assertEqual(coord, (47.3656492, 8.5248522))

    def test_retry_non_retriable_exception(self):
        self.geocoder.geocode.side_effect = [
            ValueError,
        ]
        with self.assertRaises(ValueError):
            address_to_coordinate(self.address)
