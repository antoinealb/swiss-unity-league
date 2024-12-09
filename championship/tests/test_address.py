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

from django.db.models import RestrictedError
from django.test import TestCase
from django.urls import reverse

from championship.factories import AddressFactory, EventOrganizerFactory
from championship.models import Address


class AddressListViewTest(TestCase):
    def setUp(self):
        self.organizer = EventOrganizerFactory()
        self.address = self.organizer.default_address
        self.client.force_login(self.address.organizer.user)

    def test_view_shows_address(self):
        response = self.client.get(reverse("address_list"))
        self.assertContains(response, self.address.location_name)
        self.assertContains(response, self.address.street_address)
        self.assertContains(response, self.address.city)
        self.assertContains(response, self.address.postal_code)
        self.assertContains(response, self.address.get_absolute_url())
        self.assertContains(response, self.address.get_region_display())
        self.assertContains(response, self.address.get_country_display())

    def test_shows_as_default_address(self):
        response = self.client.get(reverse("address_list"))
        self.assertContains(response, "(Main address)")

    def test_hides_delete_for_default_address(self):
        response = self.client.get(reverse("address_list"))
        self.assertNotContains(response, self.address.get_delete_url())

    def test_shows_delete_for_non_default_address(self):
        address = AddressFactory(organizer=self.organizer)
        response = self.client.get(reverse("address_list"))
        self.assertContains(response, address.get_delete_url())


class AddressCreateViewTest(TestCase):
    def setUp(self):
        self.organizer = EventOrganizerFactory()
        self.address = self.organizer.default_address
        self.client.force_login(self.address.organizer.user)

    def test_can_get(self):
        response = self.client.get(reverse("address_create"))
        self.assertEqual(response.status_code, 200)

    def test_create_new_address(self):
        self.assertEqual(Address.objects.count(), 1)
        response = self.client.post(
            reverse("address_create"),
            data={
                "location_name": "Test Location",
                "street_address": "Test Street",
                "city": "Test City",
                "postal_code": "123456",
                "region": Address.Region.AARGAU,
                "country": "CH",
                "set_as_main_address": True,
            },
        )
        self.assertEqual(Address.objects.count(), 2)
        self.assertEqual(response.url, reverse("address_list"))
        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.default_address.location_name, "Test Location")


class AddressUpdateViewTest(TestCase):
    def setUp(self):
        self.organizer = EventOrganizerFactory()
        self.address = self.organizer.default_address
        self.client.force_login(self.address.organizer.user)

    def test_can_get(self):
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
                "country": "CH",
                "set_as_main_address": False,
            },
        )
        self.assertEqual(response.url, reverse("address_list"))
        self.address.refresh_from_db()
        self.assertEqual(self.address.location_name, "New Location")
        # Make sure the default address is still the same
        self.assertEqual(self.organizer.default_address, self.address)

    def test_hides_delete_url_for_default_address(self):
        response = self.client.get(reverse("address_edit", args=[self.address.pk]))
        self.assertNotContains(response, self.address.get_delete_url())

    def test_hides_delete_url_for_non_default_address(self):
        non_default_address = AddressFactory(organizer=self.organizer)
        response = self.client.get(
            reverse("address_edit", args=[non_default_address.pk])
        )
        self.assertContains(response, non_default_address.get_delete_url())


class AddressDeleteViewTest(TestCase):
    def setUp(self):
        self.organizer = EventOrganizerFactory()
        self.address = self.organizer.default_address
        self.client.force_login(self.address.organizer.user)

    def test_delete_default_address_not_allowed(self):
        self.assertEqual(Address.objects.count(), 1)
        with self.assertRaises(RestrictedError):
            self.client.post(reverse("address_delete", args=[self.address.pk]))
        self.assertEqual(Address.objects.count(), 1)

    def test_delete_not_owned_address(self):
        other_organizer = EventOrganizerFactory()
        self.client.force_login(other_organizer.user)
        response = self.client.post(reverse("address_delete", args=[self.address.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Address.objects.filter(pk=self.address.pk).exists())


class AddressSortingTest(TestCase):
    def test_sorting(self):
        properties_in_correct_order = [
            (Address.Region.FREIBURG_DE, "B", "FR"),
            (Address.Region.FREIBURG_DE, "B", "DE"),
            (Address.Region.AARGAU, "AR", "CH"),
            (Address.Region.BERN, "aB", "CH"),
            (Address.Region.BERN, "B", "CH"),
        ]
        organizer = EventOrganizerFactory()

        sorted_addresses = sorted(
            [
                AddressFactory(
                    organizer=organizer, region=region, city=city, country=country
                )
                for region, city, country in properties_in_correct_order[::-1]
            ]
        )

        for i in range(len(properties_in_correct_order)):
            region, city, country = properties_in_correct_order[i]
            self.assertEqual(sorted_addresses[i].region, region)
            self.assertEqual(sorted_addresses[i].city, city)
            self.assertEqual(sorted_addresses[i].country, country)
