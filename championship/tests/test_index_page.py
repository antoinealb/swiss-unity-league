import datetime
from django.test import TestCase, Client
from championship.models import Event, EventOrganizer
from championship.factories import *


class HomepageTestCase(TestCase):
    """
    Tests for the landing page of the website.
    """

    def setUp(self):
        self.client = Client()

    def test_shows_title_of_next_event(self):
        """
        Checks that the home page contains a list of coming up events.
        """
        d = datetime.date.today()
        EventFactory(name="TestEvent2000", date=d, category=Event.Category.REGIONAL)
        EventFactory(name="TestEvent1000", date=d, category=Event.Category.PREMIER)
        EventFactory(name="RegularEvent", date=d, category=Event.Category.REGULAR)

        response = self.client.get("/")

        self.assertIn("TestEvent2000", response.content.decode())
        self.assertIn("TestEvent1000", response.content.decode())
        self.assertNotIn("RegularEvent", response.content.decode())

    def test_shows_player_with_points(self):
        """
        Checks that the homepage contains some player information.
        """
        player = PlayerFactory()
        EventPlayerResultFactory(player=player, points=1)
        response = self.client.get("/")
        self.assertContains(response, player.name)

    def test_hides_hidden_player_name(self):
        """
        Checks that the homepage contains some player information.
        """
        player = PlayerFactory(hidden_from_leaderboard=True)
        EventPlayerResultFactory(player=player, points=1)
        response = self.client.get("/")
        self.assertNotIn(player.name, response.content.decode())

    def test_static_files(self):
        """
        Safety check to make sure we correctly have static files.
        """
        response = self.client.get("/")
        self.assertIn("partner_logos", response.context)
        self.assertIn(
            "partner_logos/leonin_league.png", response.context["partner_logos"]
        )
