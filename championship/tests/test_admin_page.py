from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from bs4 import BeautifulSoup


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

        soup = BeautifulSoup(response.content.decode(), features="html.parser")
        self.assertIsNone(
            soup.find("a", href=reverse("admin:index")),
            "Non-staff users should not see the link to the admin page.",
        )

    def test_admin_page_shown(self):
        User.objects.create_user(username="test", password="test", is_staff=True)
        self.client.login(username="test", password="test")
        response = self.client.get("/")

        soup = BeautifulSoup(response.content.decode(), features="html.parser")
        self.assertIsNotNone(
            soup.find("a", href=reverse("admin:index")),
            "Staff users should see a link to the admin page",
        )
