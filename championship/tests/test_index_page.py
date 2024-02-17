import datetime
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from championship.models import Event
from championship.factories import *
from invoicing.factories import InvoiceFactory


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

    @override_settings(DEFAULT_SEASON=SEASON_2023)
    def test_shows_player_with_points(self):
        """
        Checks that the homepage contains some player information.
        """
        player = PlayerFactory()
        EventPlayerResultFactory(
            player=player,
            points=1,
        )
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
        EventOrganizerFactory(image="leonin_league.png")
        response = self.client.get("/")
        self.assertIn("organizers", response.context)
        self.assertIn(
            "media/leonin_league.png", response.context["organizers"][0].image.url
        )

    def test_no_open_invoice(self):
        """Checks that by default we don't have an open invoice."""
        response = self.client.get("/")
        self.assertFalse(response.context["has_open_invoices"])

    def test_open_invoice(self):
        """Checks that when an organizer has open unpaid invoices, we display a
        reminder."""
        credentials = dict(username="test", password="test")
        user = User.objects.create_user(**credentials)
        organizer = EventOrganizerFactory(user=user)
        invoice = InvoiceFactory(event_organizer=organizer)

        self.client.login(**credentials)
        response = self.client.get("/")
        self.assertTrue(response.context["has_open_invoices"])

    def test_closed_invoice(self):
        """Checks that if an invoice is paid, we don't display the banner."""
        credentials = dict(username="test", password="test")
        user = User.objects.create_user(**credentials)
        organizer = EventOrganizerFactory(user=user)
        invoice = InvoiceFactory(event_organizer=organizer)
        invoice.payment_received_date = datetime.date.today()
        invoice.save()

        self.client.login(**credentials)
        response = self.client.get("/")
        self.assertFalse(response.context["has_open_invoices"])
