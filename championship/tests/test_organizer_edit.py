from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from championship.factories import AddressFactory, EventOrganizerFactory
from championship.models import EventOrganizer


class OrganizerEditTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)

    def login(self):
        self.client.login(**self.credentials)

    def test_link_not_shown_to_anonymous_users(self):
        response = self.client.get("/")

        self.assertNotIn(
            reverse("organizer_update"),
            response.content.decode(),
            "Anonymous users should not see the link to the organizer settings page.",
        )

    def test_link_not_shown_if_no_to(self):
        """
        Checks that we don't show the link to accounts that are not TO accounts.
        """
        self.login()
        response = self.client.get("/")
        self.assertNotIn(
            reverse("organizer_update"),
            response.content.decode(),
            "Non TOs should not have the link",
        )

    def test_link_shown_when_authenticated(self):
        self.login()
        to = EventOrganizerFactory(user=self.user)
        response = self.client.get("/")
        self.assertIn(
            reverse("organizer_details", args=(to.id,)),
            response.content.decode(),
            "Logged in users should get a link to creating events",
        )

    def test_post_data(self):
        self.login()
        to = EventOrganizerFactory(user=self.user)
        new_address = to.addresses.all()[1]
        self.assertNotEqual(to.default_address.id, new_address.id)
        data = {
            "contact": "foo@foo.org",
            "name": "My test events",
            "default_address": new_address.id,
            "description": "This is a test description",
        }
        self.client.post(reverse("organizer_update"), data=data)
        to = EventOrganizer.objects.get(user=self.user)
        self.assertEqual(to.name, data["name"])
        self.assertEqual(to.contact, data["contact"])
        self.assertEqual(to.default_address.id, new_address.id)
        self.assertEqual(to.description, data["description"])
