from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from championship.factories import AddressFactory, EventOrganizerFactory
from championship.models import Address


def base_set_up(self, with_address=True, username="testuser"):
    self.client = Client()
    self.user = User.objects.create_user(username=username, password="testpass")
    self.organizer = EventOrganizerFactory(user=self.user, addresses=[])
    if with_address:
        self.address = AddressFactory()
        self.address.organizers.add(self.organizer)
    self.client.login(username=username, password="testpass")


class AddressListViewTest(TestCase):
    def setUp(self):
        base_set_up(self)

    def test_view_url_exists(self):
        response = self.client.get(reverse("address_list"))
        self.assertEqual(response.status_code, 200)

    def test_view_shows_address(self):
        response = self.client.get(reverse("address_list"))
        self.assertContains(response, str(self.address))


class AddressCreateViewTest(TestCase):
    def setUp(self):
        base_set_up(self, with_address=False)

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
                "country": "Test Country",
                "set_as_organizer_address": True,
            },
        )
        self.assertEqual(Address.objects.count(), 1)
        self.assertEqual(response.url, reverse("address_list"))
        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.default_address.location_name, "Test Location")


class AddressUpdateViewTest(TestCase):
    def setUp(self):
        base_set_up(self)

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
                "country": "New Country",
                "set_as_organizer_address": False,
            },
        )
        self.assertEqual(response.url, reverse("address_list"))
        self.address.refresh_from_db()
        self.assertEqual(self.address.location_name, "New Location")


class AddressDeleteViewTest(TestCase):
    def setUp(self):
        base_set_up(self)

    def test_delete_default_address(self):
        self.assertEqual(Address.objects.count(), 1)
        response = self.client.post(reverse("address_delete", args=[self.address.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Address.objects.count(), 0)
        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.default_address, None)

    def test_delete_not_owned_address(self):
        self.client.logout()
        base_set_up(self, with_address=False, username="testuser2")
        response = self.client.post(reverse("address_delete", args=[self.address.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Address.objects.filter(pk=self.address.pk).exists())

    def test_get_delete_view_not_allowed(self):
        # To prevent csrf only post should be allowed
        response = self.client.get(reverse("address_delete", args=[self.address.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Address.objects.filter(pk=self.address.pk).exists())
