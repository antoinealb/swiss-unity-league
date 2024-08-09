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

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from championship.factories import AddressFactory, EventOrganizerFactory
from championship.models import Address


class BaseSetupTest(TestCase):
    def base_set_up(self, with_address=True, username="testuser"):
        self.client = Client()
        self.user = User.objects.create_user(username=username, password="testpass")
        self.organizer = EventOrganizerFactory(user=self.user, addresses=[])
        if with_address:
            self.address = AddressFactory(organizer=self.organizer)
        self.client.login(username=username, password="testpass")


class AddressListViewTest(BaseSetupTest):
    def setUp(self):
        self.base_set_up()

    def test_view_url_exists(self):
        response = self.client.get(reverse("address_list"))
        self.assertEqual(response.status_code, 200)

    def test_view_shows_address(self):
        response = self.client.get(reverse("address_list"))
        self.assertContains(response, str(self.address))


class AddressCreateViewTest(BaseSetupTest):
    def setUp(self):
        self.base_set_up(with_address=False)

    def test_view_url_exists(self):
        response = self.client.get(reverse("address_create"))
        self.assertEqual(response.status_code, 200)

    def test_create_new_address(self):
        self.assertEqual(Address.objects.count(), 0)
        response = self.client.post(
            reverse("address_create"),
            data={
                "location_name": "Test Location",
                "street_address": "Test Street",
                "city": "Test City",
                "postal_code": "123456",
                "region": Address.Region.AARGAU,
                "country": Address.Country.SWITZERLAND,
                "set_as_main_address": True,
            },
        )
        self.assertEqual(Address.objects.count(), 1)
        self.assertEqual(response.url, reverse("address_list"))
        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.default_address.location_name, "Test Location")


class AddressUpdateViewTest(BaseSetupTest):
    def setUp(self):
        self.base_set_up()

    def test_view_url_exists(self):
        response = self.client.get(reverse("address_edit", args=[self.address.pk]))
        self.assertEqual(response.status_code, 200)

    def test_update_address(self):
        response = self.client.post(
            reverse("address_edit", args=[self.address.pk]),
            data={
                "location_name": "New Location",
                "street_address": "New Street",
                "city": "New City",
                "postal_code": "654321",
                "region": Address.Region.BERN,
                "country": Address.Country.SWITZERLAND,
                "set_as_main_address": False,
            },
        )
        self.assertEqual(response.url, reverse("address_list"))
        self.address.refresh_from_db()
        self.assertEqual(self.address.location_name, "New Location")


class AddressDeleteViewTest(BaseSetupTest):
    def setUp(self):
        self.base_set_up()

    def test_delete_default_address(self):
        self.assertEqual(Address.objects.count(), 1)
        response = self.client.post(reverse("address_delete", args=[self.address.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Address.objects.count(), 0)
        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.default_address, None)

    def test_delete_not_owned_address(self):
        self.client.logout()
        self.base_set_up(with_address=False, username="testuser2")
        response = self.client.post(reverse("address_delete", args=[self.address.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Address.objects.filter(pk=self.address.pk).exists())


class AddressSortingTest(TestCase):
    def test_sorting(self):
        properties_in_correct_order = [
            (Address.Region.AARGAU, "AR", Address.Country.SWITZERLAND),
            (Address.Region.BERN, "aB", Address.Country.SWITZERLAND),
            (Address.Region.BERN, "B", Address.Country.SWITZERLAND),
            (Address.Region.FREIBURG_DE, "B", Address.Country.FRANCE),
            (Address.Region.FREIBURG_DE, "B", Address.Country.GERMANY),
        ]
        to = EventOrganizerFactory(addresses=[])
        addresses = [
            AddressFactory(organizer=to, region=region, city=city, country=country)
            for region, city, country in properties_in_correct_order[::-1]
        ]
        self.assertEqual(addresses[0].region, Address.Region.FREIBURG_DE)

        sorted_addresses = sorted(addresses)

        for i in range(len(properties_in_correct_order)):
            region, city, country = properties_in_correct_order[i]
            self.assertEqual(sorted_addresses[i].region, region)
            self.assertEqual(sorted_addresses[i].city, city)
            self.assertEqual(sorted_addresses[i].country, country)
