import datetime
import os.path

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from championship.models import Event, EventOrganizer, EventPlayerResult
from championship.aetherhub_parser import parse_standings_page
from championship.factories import *

from unittest.mock import patch, MagicMock


def load_test_html(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path) as f:
        text = f.read()
    return text


def parse_standings_html(filename):
    text = load_test_html(filename)
    return list(parse_standings_page(text))


class AetherhubStandingsParser(TestCase):
    def setUp(self):
        self.results = parse_standings_html("aetherhub_ranking.html")

    def test_can_parse(self):
        wantStandings = [
            ("DarioMazzola", 13, "4 - 0 - 1"),
            ("Dominik Horber", 13, "4 - 0 - 1"),
            ("Christopher Weber", 12, "4 - 1"),
        ]
        self.assertEqual(wantStandings, self.results[:3])


class AetherhubImportTest(TestCase):
    """
    Tests for the feature that create new events for tournament organizers.
    """

    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizer.objects.create(
            name="test TO", contact="", user=self.user
        )
        self.event = EventFactory(organizer=self.organizer)

        self.data = {
            "url": "https://aetherhub.com/Tourney/RoundTourney/13923",
            "event": self.event.id,
        }

    def login(self):
        self.client.login(**self.credentials)

    def mock_response(self, requests_get):
        resp = MagicMock()
        resp.content = load_test_html("aetherhub_ranking.html").encode()
        requests_get.return_value = resp

    def test_link_not_shown_to_anonymous_users(self):
        response = self.client.get("/")

        self.assertNotIn(
            reverse("results_create"),
            response.content.decode(),
            "Anonymous users should not see the link upload results.",
        )

    def test_link_shown_when_authenticated(self):
        self.login()
        response = self.client.get("/")
        self.assertIn(
            reverse("results_create"),
            response.content.decode(),
            "Logged in users should get a link to uploading results",
        )

    @patch("requests.get")
    def test_get_url(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        self.client.post(reverse("results_create"), self.data)

        got_url = requests_get.call_args[0][0]
        self.assertEqual(got_url, self.data["url"])

    @patch("requests.get")
    def test_imports_result_for_correct_tourney(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        response = self.client.post(reverse("results_create"), self.data)

        results = EventPlayerResult.objects.filter(event=self.event).order_by(
            "-points"
        )[:]

        # hardcoded spot checks from the tournament
        self.assertEqual(len(results), 30)
        self.assertEqual(results[0].points, 13)
        self.assertEqual(results[10].points, 9)
        self.assertEqual(results[27].points, 3)
