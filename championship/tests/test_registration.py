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
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.status import HTTP_429_TOO_MANY_REQUESTS

from championship.models import Address, EventOrganizer


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
            "country": "CH",
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
        self.assertContains(response, "Please enter a correct username and password.")
        user = User.objects.get(email=self.data["email"])
        user.is_active = True
        user.save()
        response = self.client.post(
            reverse("login"),
            data={"username": self.username, "password": self.data["password1"]},
        )
        self.assertRedirects(response, reverse("index"))

    def test_username_already_taken(self):
        User.objects.create_user(username=self.username)
        response = self.client.post(reverse("register"), data=self.data)
        self.assertContains(
            response,
            "An account with this name already exists. We will contact you shortly.",
        )
        self.assertFalse(User.objects.filter(email=self.data["email"]).exists())

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_rate_limit_submission(self):
        """Test that registrations are capped per IP.

        Note that the rate limit implementation uses the cache to store its
        state, so we need to override a functioning cache for this test.."""
        # First, normal response
        self.client.post(reverse("register"), data=self.data)

        # Second response will be rate limited
        response = self.client.post(reverse("register"), data=self.data)
        self.assertEqual(HTTP_429_TOO_MANY_REQUESTS, response.status_code)

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_invalid_forms_do_not_eat_quota(self):
        """Check that forms returned with an error do not eat into the quota,
        as this leads to a user being unable to change their mistake and
        retry.."""
        # First, normal response for something invalid
        self.data["email"] = "not_an_email"
        self.client.post(reverse("register"), data=self.data)
        self.assertFalse(User.objects.all().exists())

        self.data["email"] = "an_email@gmail.com"
        resp = self.client.post(reverse("register"), data=self.data)
        self.assertEqual(200, resp.status_code)
        self.assertTrue(User.objects.all().exists())
