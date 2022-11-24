import datetime
from django.test import TestCase, Client
from championship.models import Event, EventOrganizer
from championship.factories import *


class AdminViewTestCase(TestCase):
    """
    Tests for the landing page of the website.
    """

    def setUp(self):
        self.client = Client()

    def test_shows_title_of_next_event(self):
        """
        Checks that the home page contains a list of coming up events.
        """
        d = datetime.date.today() + datetime.timedelta(days=1)
        event = EventFactory(name="TestEvent2000", date=d)

        response = self.client.get("/")

        self.assertIn("TestEvent2000", response.content.decode())

    def test_shows_player_name(self):
        """
        Checks that the homepage contains some player information.
        """
        player = PlayerFactory()
        response = self.client.get("/")
        self.assertIn(player.first_name, response.content.decode())
        self.assertIn(player.last_name, response.content.decode())
