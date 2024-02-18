from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from championship.models import EventOrganizer
from championship.models import Address


class OrganizerRegistrationTestCase(TestCase):

    def setUp(self):
        self.data = {
            "first_name": "First##",
            "last_name": "Last",
            "password1": "ah18afh8as",
            "password2": "ah18afh8as",
            "email": "test@example.com",
            "name": "Organizer Name",
            "contact": "invoice@mail.com",
            "url": "http://example.com",
            "description": "This is a test description",
            "location_name": "Test Location",
            "street_address": "Test Street",
            "postal_code": "123456",
            "city": "Test City",
            "region": Address.Region.AARGAU,
            "country": Address.Country.SWITZERLAND,
        }
        self.username = "organizer-name_first"

    def test_registration(self):
        response = self.client.post(reverse("register"), data=self.data)
        self.assertContains(response, "Application Submitted")
        user = User.objects.get(email=self.data["email"])
        organizer = EventOrganizer.objects.get(user=user)
        self.assertEqual(user.first_name, self.data["first_name"])
        self.assertEqual(user.username, self.username)
        self.assertEqual(organizer.name, self.data["name"])
        self.assertEqual(organizer.contact, self.data["contact"])
        self.assertEqual(organizer.url, self.data["url"])
        self.assertEqual(organizer.description, self.data["description"])
        self.assertEqual(
            organizer.default_address.location_name, self.data["location_name"]
        )
        self.assertEqual(
            organizer.default_address.street_address, self.data["street_address"]
        )
        self.assertEqual(
            organizer.default_address.postal_code, self.data["postal_code"]
        )
        self.assertEqual(organizer.default_address.city, self.data["city"])
        self.assertEqual(organizer.default_address.region, self.data["region"])
        self.assertEqual(organizer.default_address.country, self.data["country"])

    def test_user_cant_login_before_approval(self):
        self.client.post(reverse("register"), data=self.data)
        response = self.client.post(
            reverse("login"),
            data={"username": self.username, "password": self.data["password1"]},
        )
        text = response.content.decode("utf-8")
        self.assertContains(response, "Please enter a correct username and password.")
        user = User.objects.get(email=self.data["email"])
        user.is_active = True
        user.save()
        response = self.client.post(
            reverse("login"),
            data={"username": self.username, "password": self.data["password1"]},
        )
        self.assertRedirects(response, reverse("index"))
