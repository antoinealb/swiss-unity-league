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

import datetime

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.test import Client, TestCase
from django.utils import timezone

from parameterized import parameterized
from waffle.testutils import override_flag

from articles.factories import ArticleFactory
from championship.factories import (
    EventFactory,
    EventOrganizerFactory,
    PlayerFactory,
    ResultFactory,
)
from championship.models import Address, Event
from invoicing.factories import InvoiceFactory
from multisite.constants import ALL_DOMAINS
from multisite.tests.utils import with_site


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

        self.assertContains(response, "TestEvent2000")
        self.assertContains(response, "TestEvent1000")
        self.assertNotContains(response, "RegularEvent")

    def test_premier_events_prioritized(self):
        """Checks that up to 3 premier events are shown even if there are several regional events before them."""
        d = datetime.date.today()
        premiers = [
            EventFactory(
                date=(d + datetime.timedelta(days=i)), category=Event.Category.PREMIER
            )
            for i in range(5)
        ]
        regionals = [
            EventFactory(date=d, category=Event.Category.REGIONAL) for i in range(5)
        ]
        got_events = self.client.get("/").context["future_events"]
        expected_events = regionals[:2] + premiers[:3]
        self.assertEqual(set(got_events), set(expected_events))

    def test_premier_events_are_shown_first_on_given_date(self):
        """
        Checks that if a regianal and a premier are on the same date, the
        premier event is listed first, as we want to promote those more.
        """
        event_date = datetime.date.today() + datetime.timedelta(days=7)
        for category in [Event.Category.PREMIER, Event.Category.REGIONAL]:
            EventFactory(date=event_date, category=category)

        got_events = self.client.get("/").context["future_events"]
        got_categories = [e.category for e in got_events]
        want_categories = [Event.Category.PREMIER, Event.Category.REGIONAL]
        self.assertEqual(
            got_categories,
            want_categories,
            "Premier events should be listed before Regional events.",
        )

    def test_shows_player_with_points(self):
        """
        Checks that the homepage contains some player information.
        """

        result = ResultFactory(
            points=1,
            event__date=datetime.date.today() - datetime.timedelta(days=1),
            event__category=Event.Category.REGULAR,
        )
        response = self.client.get("/")
        self.assertContains(response, result.player.name)

    def test_hides_hidden_player_name(self):
        """
        Checks that the homepage contains some player information.
        """
        player = PlayerFactory(hidden_from_leaderboard=True)
        ResultFactory(player=player, points=1)
        response = self.client.get("/")
        self.assertNotIn(player.name, response.content.decode())

    def test_static_files(self):
        """
        Safety check to make sure we correctly have static files.
        """
        organizer = EventOrganizerFactory(image="leonin_league.png")
        EventFactory(organizer=organizer, date=datetime.date.today())
        response = self.client.get("/")
        self.assertIn("organizers", response.context)
        self.assertIn(
            "media/leonin_league.png", response.context["organizers"][0].image.url
        )

    def test_images_only_shows_recent_organizers(self):
        organizer = EventOrganizerFactory(image="leonin_league.png")
        EventFactory(organizer=organizer, date=datetime.date.today())

        organizer = EventOrganizerFactory(image="GBB.png")
        EventFactory(
            organizer=organizer,
            date=datetime.date.today() - datetime.timedelta(days=365),
        )

        organizer = EventOrganizerFactory(image="lotus.png")

        response = self.client.get("/")
        self.assertIn("organizers", response.context)
        self.assertEqual(len(response.context["organizers"]), 1)

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
        InvoiceFactory(event_organizer=organizer)

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

    def test_no_pending_registration(self):
        """Checks that by default we don't have a pending registration."""
        response = self.client.get("/")
        self.assertFalse(response.context["has_pending_registration"])

    def test_pending_registration(self):
        data = {
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

        response = self.client.post(reverse("register"), data=data)

        self.admin_user = User.objects.create_superuser(
            username="admin", password="password123", email="admin@example.com"
        )
        self.client.login(username="admin", password="password123")

        response = self.client.get("/")
        self.assertTrue(response.context["has_pending_registration"])

    def test_hides_unpublished_articles(self):
        articles = [
            ArticleFactory(
                published_date=timezone.now().date() + timezone.timedelta(days=1)
            ),
            ArticleFactory(),
        ]
        response = self.client.get("/")
        for article in articles:
            self.assertNotContains(response, article.title)

    @override_flag("index_article_card_show_header", active=True)
    def test_when_image_shows_no_description(self):
        article = ArticleFactory(
            published_date=timezone.now().date(),
            header_image="header.jpg",
        )
        response = self.client.get("/")
        self.assertContains(response, article.title)
        self.assertNotContains(response, article.description)
        self.assertContains(response, article.header_image.url)
        self.assertContains(response, article.get_absolute_url())

    def test_article_without_image(self):
        article = ArticleFactory(
            published_date=timezone.now().date(),
        )
        response = self.client.get("/")
        self.assertContains(response, article.title)
        self.assertContains(response, article.description)
        self.assertContains(response, article.get_absolute_url())

    def test_article_without_description_shows_truncated_content(self):
        article = ArticleFactory(
            published_date=timezone.now().date(),
            description="",
            content="<p>This is a test content</p>",
        )
        response = self.client.get("/")
        self.assertContains(response, article.title)
        self.assertContains(response, "This is a test content")
        self.assertContains(response, article.get_absolute_url())

    def test_shows_contact_email(self):
        response = self.client.get("/")
        self.assertContains(
            response, Site.objects.get_current().site_settings.contact_email
        )

    @parameterized.expand(ALL_DOMAINS)
    def test_shows_site_specific_abstract(self, domain):
        with with_site(domain):
            resp = self.client.get("/")
            expected_abstract = render_to_string(
                f"info/{domain}/abstract.html", {"SITE": Site.objects.get_current()}
            )
            self.assertContains(resp, expected_abstract)

    @parameterized.expand(ALL_DOMAINS)
    def test_shows_site_specific_name(self, domain):
        with with_site(domain):
            resp = self.client.get("/")
            sites = Site.objects.all()
            for site in sites:
                if site.domain == domain:
                    self.assertContains(resp, site.name)
                else:
                    self.assertNotContains(resp, site.name)
