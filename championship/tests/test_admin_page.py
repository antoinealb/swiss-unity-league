from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


class AdminViewTestCase(TestCase):
    """
    Tests how the admin page is integrated in our website.

    We don't test the admin view itself (it should be tested by Django), but we
    check things like "is the adming page link only shown to staff users?"
    """

    def setUp(self):
        self.client = Client()

    def test_no_admin_page_shown(self):
        response = self.client.get("/")

        self.assertNotIn(
            reverse("admin:index"),
            response.content.decode(),
            "Non-staff users should not see the link to the admin page.",
        )

    def test_admin_page_shown(self):
        User.objects.create_user(username="test", password="test", is_staff=True)
        self.client.login(username="test", password="test")
        response = self.client.get("/")
        self.assertIn(
            reverse("admin:index"),
            response.content.decode(),
            "Staff users should see a link to the admin page",
        )
