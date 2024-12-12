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

from unittest import mock

from django.test import TestCase
from django.test.client import RequestFactory

from geoip2.errors import AddressNotFoundError

from geo.middleware import GeoIpMiddleware


class GeoIpMiddlewareTest(TestCase):
    city_data = {
        "city": "Bern",
        "country_code": "CH",
        "latitude": 47.0,
        "longitude": 48.0,
    }

    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = mock.MagicMock()
        self.geoip_mock = mock.Mock()
        self.geoip_mock.city.return_value = self.city_data
        self.middleware = GeoIpMiddleware(self.get_response, geoip=self.geoip_mock)

        self.request = self.factory.get("/", REMOTE_ADDR="103.214.95.1")

    def assertHasGeoIPData(self, request):
        self.assertTrue(
            hasattr(request, "geoip_data"),
            "GeoIP data should be attached to the request",
        )

    def test_middleware_forwards_request(self):
        resp = self.middleware(self.request)
        self.get_response.assert_called_with(self.request)
        self.assertEqual(resp, self.get_response.return_value)

    def test_middleware_looks_up_geo_ip(self):
        self.middleware(self.request)
        processed_request = self.get_response.call_args[0][0]
        self.assertHasGeoIPData(processed_request)
        self.assertEqual("Bern", processed_request.geoip_data.city)
        self.assertEqual("CH", processed_request.geoip_data.country_code)
        self.geoip_mock.city.assert_any_call("103.214.95.1")

    def test_middleware_looks_up_geo_ip_proxy(self):
        self.request.META["HTTP_X_FORWARDED_FOR"] = self.request.META["REMOTE_ADDR"]
        del self.request.META["REMOTE_ADDR"]

        self.middleware(self.request)
        processed_request = self.get_response.call_args[0][0]
        self.assertHasGeoIPData(processed_request)
        self.assertEqual("Bern", processed_request.geoip_data.city)
        self.assertEqual("CH", processed_request.geoip_data.country_code)
        self.assertEqual(47.0, processed_request.geoip_data.latitude)
        self.assertEqual(48.0, processed_request.geoip_data.longitude)
        self.geoip_mock.city.assert_any_call("103.214.95.1")

    def test_ip_not_in_db(self):
        self.geoip_mock.city.side_effect = AddressNotFoundError("not found")
        self.middleware(self.request)
        processed_request = self.get_response.call_args[0][0]
        self.assertIsNone(processed_request.geoip_data)
