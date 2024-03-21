from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from championship.factories import EventFactory, EventOrganizerFactory
from championship.models import *


class TestEventListAPI(APITestCase):
    def setUp(self):
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)

    def test_list_all(self):
        resp = self.client.get(reverse("organizers-list")).json()
        self.assertEqual(1, len(resp))
        self.assertEqual(self.organizer.id, resp[0]["id"])
        self.assertEqual(self.organizer.name, resp[0]["name"])
        self.assertEqual([], resp[0]["events"])

    def test_list_event(self):
        e = EventFactory(organizer=self.organizer)
        resp = self.client.get(reverse("organizers-list")).json()
        self.assertEqual(1, len(resp))
        url = reverse("events-detail", args=[e.id])
        url = f"http://testserver{url}"
        self.assertEqual([url], resp[0]["events"])

    def test_get_me(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse("organizers-me")).json()
        self.assertEqual(resp["name"], self.organizer.name)
