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

from django.contrib.gis.geos import Point
from django.test import TestCase

from championship.factories import AddressFactory


class AddressGeocodingTest(TestCase):
    def test_address_gets_geocoded(self):
        """
        Checks that Addresses get geo-coded (converted to lat/lon) on save().

        When testing we use a fake geocoder that always returns the same address.
        """
        a = AddressFactory()
        self.assertAlmostEqual(47.38, a.position.x, places=2)
        self.assertAlmostEqual(8.53, a.position.y, places=2)

    def test_address_gets_geocoded_on_updated(self):
        """
        When testing we use a fake geocoder that always returns the same address.
        """
        a = AddressFactory()
        a.position = Point(1.0, 2.0, srid=4326)
        a.save()

        # Checks that it got geocoded again
        self.assertAlmostEqual(47.38, a.position.x, places=2)
        self.assertAlmostEqual(8.53, a.position.y, places=2)
