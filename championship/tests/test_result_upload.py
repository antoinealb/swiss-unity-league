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
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from parameterized import parameterized
from requests import HTTPError

from championship.factories import (
    EventOrganizerFactory,
    PlayerFactory,
    RankedEventFactory,
    ResultFactory,
)
from championship.forms import AddTop8ResultsForm
from championship.models import Event, Player, PlayerAlias, Result, clean_name
from championship.parsers.challonge import TournamentNotSwissError
from championship.tests.parsers.utils import load_test_html, load_test_json


class CleanNameTest(TestCase):
    @parameterized.expand(
        [
            "AntoineAlbertelli",
            "Antoine ALBERTELLI",
            "Antoine ALBertelli",
            "AntoineALBERTELLI",
            "Antoine_Albertelli",
            "   Antoine      Albertelli   ",
            "antoine albertelli",
            "Antoine Albertelli",
        ]
    )
    def test_clean_basic(self, name):
        want = "Antoine Albertelli"
        self.assertEqual(want, clean_name(name))

    def test_dash(self):
        self.assertEqual("Antoine Renaud-Goud", clean_name("antoine renaud-goud"))

    def test_dot(self):
        self.assertEqual("Thomas J. Kardos", clean_name("thomas j. kardos"))

    def test_numbers(self):
        self.assertEqual("Renki777", clean_name("Renki777"))

    def test_short_words_shouldnt_be_capital(self):
        self.assertEqual("Laurin van der Hagen", clean_name("laurin van der hagen"))
        self.assertEqual("Laurin Van Der Hagen", clean_name("laurin Van Der hagen"))


class AetherhubImportTest(TestCase):
    """
    Tests for the feature that create new events for tournament organizers.
    """

    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category.REGULAR,
        )

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

        self.client.post(reverse("results_create_aetherhub"), self.data)

        got_url = requests_get.call_args[0][0]
        self.assertEqual(got_url, self.data["url"])

    @patch("requests.get")
    def test_get_with_edit_url(self, requests_get):
        """By default Aetherhub displays the EditTourney view to the tournament
        admin. We want to convert that to the RoundTourney URL before getting
        the results."""
        self.login()
        self.mock_response(requests_get)

        self.data["url"] = "https://aetherhub.com/Tourney/EditTourney/15671"

        self.client.post(reverse("results_create_aetherhub"), self.data)

        got_url = requests_get.call_args[0][0]
        want_url = "https://aetherhub.com/Tourney/RoundTourney/15671"
        self.assertEqual(got_url, want_url)

    @patch("requests.get")
    def test_imports_result_for_correct_tourney(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        self.client.post(reverse("results_create_aetherhub"), self.data)

        results = Result.objects.filter(event=self.event).order_by("id")[:]

        # hardcoded spot checks from the tournament
        self.assertEqual(len(results), 30)
        self.assertEqual(results[0].points, 13)
        self.assertEqual(results[0].draw_count, 1)
        self.assertEqual(results[0].loss_count, 0)
        self.assertEqual(results[0].win_count, 4)
        self.assertEqual(results[0].ranking, 1)
        self.assertEqual(results[10].points, 9)
        self.assertEqual(results[10].ranking, 11)
        self.assertEqual(results[27].points, 3)
        self.assertEqual(results[27].ranking, 28)

        # Check that CamelCase conversion works
        Player.objects.get(name="Amar Zehic")

    @patch("requests.get")
    def test_imports_result_with_aliasing(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        orig_player = PlayerFactory(name="Test Player")
        PlayerAlias.objects.create(name="Dominik Horber", true_player=orig_player)

        self.client.post(reverse("results_create_aetherhub"), self.data)

        results = Result.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[1].player.name, "Test Player")

    @patch("requests.get")
    def test_imports_result_for_different_tourney_resuses_player(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        # Import the first event
        self.client.post(reverse("results_create_aetherhub"), self.data)

        # Create a second event, and import the results again
        second_event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=self.event.category,
        )
        self.data["event"] = second_event.id
        self.client.post(reverse("results_create_aetherhub"), self.data)

        # Check that a random player has indeed two events to their name
        player = Player.objects.all()[0]
        results = Result.objects.filter(player=player).count()
        self.assertEqual(2, results, "Each player should have two results")

    @patch("requests.get")
    def test_imports_result_cleans_space_in_name(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        # Import the first event
        self.client.post(reverse("results_create_aetherhub"), self.data)

        # This player in the mock result contains too many space between name
        # and first name
        Player.objects.get(name="Pavel Malach")

    @patch("requests.get")
    def test_redirects_after_reply(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        # Import the first event
        resp = self.client.post(
            reverse("results_create_aetherhub"), self.data, follow=True
        )
        self.assertRedirects(resp, self.event.get_absolute_url())

    @patch("requests.get")
    def test_correctly_handles_backend_errors(self, requests_get):
        self.login()
        requests_get.side_effects = HTTPError()

        resp = self.client.post(reverse("results_create_aetherhub"), self.data)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Could not fetch standings", resp.content.decode())

    @patch("requests.get")
    def test_correctly_handles_backend_redirects(self, requests_get):
        self.login()
        resp = MagicMock()
        redirect_resp = MagicMock()
        redirect_resp.status_code = 302
        resp.history = [redirect_resp]
        requests_get.return_value = resp

        resp = self.client.post(reverse("results_create_aetherhub"), self.data)

        self.assertContains(resp, "The tournament was not found.")

    @patch("requests.get")
    def test_correctly_handles_unfinished_tournaments(self, requests_get):
        self.login()
        resp = MagicMock()
        resp.content = (
            load_test_html("aetherhub_ranking.html").replace("Finished:", "").encode()
        )
        resp.status_code = 200
        requests_get.return_value = resp

        resp = self.client.post(reverse("results_create_aetherhub"), self.data)

        self.assertContains(resp, "The tournament is not finished.")

    def test_correctly_handles_wrong_url(self):
        self.login()
        self.data["url"] = "https://challonge.com/de/32qwqta"

        resp = self.client.post(reverse("results_create_aetherhub"), self.data)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Wrong url format.", resp.content.decode())

    def _choices(self, response):
        choices = list(response.context["form"].fields["event"].choices)
        choices = [s[0].instance for s in choices[1:]]
        return choices

    def test_only_allows_selection_of_events_with_no_results(self):
        """Checks that the user is only offered to upload results to
        tournaments that don't have results yet."""
        self.login()

        # First, check that we have our event offered
        response = self.client.get(reverse("results_create_aetherhub"))
        gotChoices = self._choices(response)
        wantChoices = [self.event]
        self.assertEqual(gotChoices, wantChoices)

        # Then create results for the event and makes sure we don't have the
        # event listed anymore
        Result.objects.create(
            points=10,
            player=PlayerFactory(),
            event=self.event,
            ranking=1,
            win_count=3,
            draw_count=1,
            loss_count=0,
        )
        response = self.client.get(reverse("results_create_aetherhub"))
        gotChoices = self._choices(response)
        self.assertEqual([], gotChoices)

    def test_category_other_not_allowed_choice(self):
        self.login()
        RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category.OTHER,
        )
        response = self.client.get(reverse("results_create_aetherhub"))
        gotChoices = self._choices(response)
        self.assertEqual([self.event], gotChoices)


class SpicerackLinkImportTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category.REGULAR,
        )

        self.data = {
            "url": "https://www.spicerack.gg/admin/events/1182690#setup",
            "event": self.event.id,
        }

    def login(self):
        self.client.login(**self.credentials)

    def post_form(self):
        return self.client.post(reverse("results_create_spicerack"), self.data)

    def mock_response(self, requests_get):
        resp1 = MagicMock()
        resp1.json.return_value = load_test_json("spicerack/get_all_rounds.json")

        resp2 = MagicMock()
        resp2.json.return_value = load_test_json("spicerack/include_all_standings.json")
        requests_get.side_effect = [resp1, resp2]

    @patch("requests.get")
    def test_imports_result_for_correct_tourney(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        self.post_form()

        results = Result.objects.filter(event=self.event).order_by("id")[:]

        self.assertEqual(len(results), 17)
        player_id = 1
        self.assertEqual(results[player_id].points, 11)
        self.assertEqual(results[player_id].draw_count, 2)
        self.assertEqual(results[player_id].loss_count, 0)
        self.assertEqual(results[player_id].win_count, 3)
        self.assertEqual(results[player_id].ranking, 2)

    def test_correctly_handles_wrong_url(self):
        self.login()
        self.data["url"] = "https://wrongsite.com/Tourney/RoundTourney/13923"

        resp = self.post_form()

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Wrong url format.")


class ChallongeLinkImportTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category.REGULAR,
        )

        self.data = {
            "url": "https://challonge.com/de/sdisxw8g",
            "event": self.event.id,
        }

    def login(self):
        self.client.login(**self.credentials)

    def post_form(self):
        return self.client.post(reverse("challonge_create_link_results"), self.data)

    def mock_response(self, requests_get):
        resp = MagicMock()
        resp.content = load_test_html("challonge_new_ranking.html").encode()
        requests_get.return_value = resp

    @patch("requests.get")
    def test_imports_result_for_correct_tourney(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        self.post_form()

        results = Result.objects.filter(event=self.event).order_by("id")[:]

        self.assertEqual(len(results), 14)
        player_id = 1
        self.assertEqual(results[player_id].points, 9)
        self.assertEqual(results[player_id].draw_count, 0)
        self.assertEqual(results[player_id].loss_count, 1)
        self.assertEqual(results[player_id].win_count, 3)
        self.assertEqual(results[player_id].ranking, 2)

    @patch("requests.get")
    def test_swiss_round_error(self, requests_get):
        self.login()
        resp = MagicMock()
        resp.content = (
            load_test_html("challonge_new_ranking.html")
            .replace("Swiss", "Round Robin")
            .encode()
        )
        requests_get.return_value = resp

        response = self.post_form()

        self.assertContains(response, TournamentNotSwissError.ui_error_message)

    def test_correctly_handles_wrong_url(self):
        self.login()
        self.data["url"] = "https://aetherhub.com/Tourney/RoundTourney/13923"

        resp = self.post_form()

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Wrong url format.", resp.content.decode())


class ChallongeHtmlImportTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category,
        )

        text = load_test_html("challonge_new_ranking.html")

        standings = SimpleUploadedFile(
            "standings", text.encode(), content_type="text/html"
        )

        self.data = {
            "standings": standings,
            "event": self.event.id,
        }

    def login(self):
        self.client.login(**self.credentials)

    def post_form(self):
        return self.client.post(reverse("results_create_challonge"), self.data)

    def test_imports_result_for_correct_tourney(self):
        self.login()

        self.post_form()

        results = Result.objects.filter(event=self.event).order_by("id")[:]

        # hardcoded spot checks from the tournament
        self.assertEqual(len(results), 14)
        self.assertEqual(results[0].points, 12)
        self.assertEqual(results[0].ranking, 1)
        self.assertEqual(results[3].points, 9)
        self.assertEqual(results[3].ranking, 4)
        self.assertEqual(results[0].player.name, "Pascal Richter")

    def test_import_result_with_aliasing(self):
        self.login()

        orig_player = PlayerFactory(name="Test Player")
        PlayerAlias.objects.create(name="Pascal Richter", true_player=orig_player)

        self.post_form()
        results = Result.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].player.name, "Test Player")

    def test_import_garbage(self):
        """Checks that when we try to import garbage data, we get a nice error
        message instead of a 500."""

        self.data["standings"] = SimpleUploadedFile(
            "standings", "FOOBAR".encode(), content_type="text/html"
        )

        self.login()
        resp = self.post_form()
        self.assertEqual(200, resp.status_code)
        self.assertIn("Could not parse standings", resp.content.decode())


class EventLinkImportTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category,
        )

        text = load_test_html("eventlink_ranking.html")

        standings = SimpleUploadedFile(
            "standings", text.encode(), content_type="text/html"
        )

        self.data = {
            "standings": standings,
            "event": self.event.id,
        }

    def login(self):
        self.client.login(**self.credentials)

    def test_imports_result_for_correct_tourney(self):
        self.login()

        self.client.post(reverse("results_create_eventlink"), self.data)

        results = Result.objects.filter(event=self.event).order_by("id")[:]

        # hardcoded spot checks from the tournament
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0].points, 10)
        self.assertEqual(results[0].ranking, 1)
        self.assertEqual(results[3].points, 6)
        self.assertEqual(results[3].ranking, 4)
        self.assertEqual(results[0].player.name, "Jeremias Wildi")

    def test_import_result_with_aliasing(self):
        self.login()

        orig_player = PlayerFactory(name="Test Player")
        PlayerAlias.objects.create(name="Jeremias Wildi", true_player=orig_player)

        self.client.post(reverse("results_create_eventlink"), self.data)
        results = Result.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].player.name, "Test Player")

    def test_import_garbage(self):
        """Checks that when we try to import garbage data, we get a nice error
        message instead of a 500."""

        self.data["standings"] = SimpleUploadedFile(
            "standings", "FOOBAR".encode(), content_type="text/html"
        )

        self.login()
        resp = self.client.post(reverse("results_create_eventlink"), self.data)
        self.assertEqual(200, resp.status_code)
        self.assertIn("Could not parse standings", resp.content.decode())

    def test_only_allows_selection_of_events_with_no_results(self):
        """Checks that the user is only offered to upload results to
        tournaments that don't have results yet."""
        self.login()

        def _choices(response):
            choices = list(response.context["form"].fields["event"].choices)
            choices = [s[0].instance for s in choices[1:]]
            return choices

        # First, check that we have our event offered
        response = self.client.get(reverse("results_create_eventlink"))
        gotChoices = _choices(response)
        wantChoices = [self.event]
        self.assertEqual(gotChoices, wantChoices)

        # Then create results for the event and makes sure we don't have the
        # event listed anymore
        ResultFactory(event=self.event)
        response = self.client.get(reverse("results_create_eventlink"))
        gotChoices = _choices(response)
        self.assertEqual([], gotChoices)

    def test_record_not_reflecting_match_points(self):
        self.data["standings"] = SimpleUploadedFile(
            "standings",
            load_test_html("eventlink_ranking_wrong_record.html").encode(),
            content_type="text/html",
        )

        self.login()
        resp = self.client.post(reverse("results_create_eventlink"), self.data)
        self.assertEqual(200, resp.status_code)
        self.assertContains(
            resp, "The record of Jeremias Wildi does not add up to the match points."
        )


class MeleeUploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category.PREMIER,
            results_validation_enabled=False,
        )

        text = load_test_html("melee_standings.csv")

        standings = SimpleUploadedFile(
            "standings", text.encode(), content_type="text/csv"
        )

        self.data = {
            "standings": standings,
            "event": self.event.id,
        }

    def login(self):
        self.client.login(**self.credentials)

    def test_imports_result_for_correct_tourney(self):
        self.login()

        self.client.post(reverse("results_create_melee"), self.data)
        results = Result.objects.filter(event=self.event).order_by("id")[:]

        self.assertEqual(len(results), 39)
        self.assertEqual(results[0].points, 29)
        self.assertEqual(results[0].ranking, 1)
        self.assertEqual(results[0].player.name, "Antoine Renaud-Goud")

        self.assertEqual(results[2].points, 28)
        self.assertEqual(results[2].ranking, 3)
        self.assertEqual(results[2].player.name, "Christian Rothen")


class MtgEventUploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category.REGULAR,
        )

        text = load_test_html("mtgevent_ranking.html")

        standings = SimpleUploadedFile(
            "standings", text.encode(), content_type="text/html"
        )

        self.data = {
            "standings": standings,
            "event": self.event.id,
        }

    def login(self):
        self.client.login(**self.credentials)

    def test_imports_result(self):
        self.login()

        self.client.post(reverse("results_create_mtgevent"), self.data)

        self.event.refresh_from_db()

        results = self.event.result_set.order_by("ranking")
        self.assertEqual(results.count(), 10)
        self.assertEqual(results[0].player.name, "Toni Marty")

    def test_premier_event_downgraded_to_regional(self):
        self.login()
        self.event.category = Event.Category.PREMIER
        self.event.save()
        resp = self.client.post(
            reverse("results_create_mtgevent"), self.data, follow=True
        )
        self.assertEqual(200, resp.status_code)
        self.assertContains(resp, "this event was downgraded to SUL Regional")
        self.assertTrue(self.event.result_set.exists())

    def test_disable_tournament_validation(self):
        """Check that we can disable event results validation in case a
        tournament requires it (e.g. because of byes)."""
        self.login()
        self.event.category = Event.Category.PREMIER
        self.event.results_validation_enabled = False
        self.event.save()
        self.client.post(reverse("results_create_mtgevent"), self.data)
        self.assertTrue(
            self.event.result_set.exists(),
            "Results should have been created.",
        )


class ExcelCsvUploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category.REGULAR,
        )

    def login(self):
        self.client.login(**self.credentials)

    def test_upload_excel_results(self):
        self.login()

        with open("championship/tests/parsers/excel_ranking.xlsx", "rb") as f:
            standings = SimpleUploadedFile(
                "standings.xlsx",
                f.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        self.data = {
            "standings": standings,
            "event": self.event.id,
        }

        self.client.post(reverse("results_create_excelcsv"), self.data)
        self.event.refresh_from_db()

        results = self.event.result_set.order_by("ranking")
        self.assertEqual(results.count(), 3)
        self.assertEqual(results[0].player.name, "Jari Rentsch")
        self.assertEqual(results[0].ranking, 1)
        self.assertEqual(results[0].points, 9)
        self.assertEqual(results[0].win_count, 3)
        self.assertEqual(results[0].draw_count, 0)
        self.assertEqual(results[0].loss_count, 1)

    def test_upload_csv_results(self):
        test_csv = """RECORD,PLAYER_NAME
        3-0-1,Player 1
        2-2-0,Player 2
        1-3-0,Player 3"""

        self.login()

        standings = SimpleUploadedFile(
            "standings.csv",
            test_csv.encode(),
            content_type="text/csv",
        )

        self.data = {
            "standings": standings,
            "event": self.event.id,
        }
        self.client.post(reverse("results_create_excelcsv"), self.data)
        self.event.refresh_from_db()

        results = self.event.result_set.order_by("ranking")
        self.assertEqual(results.count(), 3)
        self.assertEqual(results[0].player.name, "Player 1")
        self.assertEqual(results[0].ranking, 1)
        self.assertEqual(results[0].points, 10)
        self.assertEqual(results[0].win_count, 3)
        self.assertEqual(results[0].draw_count, 1)
        self.assertEqual(results[0].loss_count, 0)

    def test_ui_error_message(self):
        wrong_csv = """R,PLAYER_NAME
        3-0-1,Player 1
        2-2-0,Player 2
        1-3-0,Player 3"""

        self.login()

        standings = SimpleUploadedFile(
            "standings.csv",
            wrong_csv.encode(),
            content_type="text/csv",
        )

        self.data = {
            "standings": standings,
            "event": self.event.id,
        }
        response = self.client.post(reverse("results_create_excelcsv"), self.data)
        response_text = response.content.decode()
        self.assertTrue("RECORD or MATCH_POINTS was not found" in response_text)


class ManualImportTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
            category=Event.Category.REGULAR,
        )

        self.data = {
            "form-0-name": "Antoine Albertelli",
            "form-0-points": "3-0-1",
            "event": self.event.id,
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 1,
            "form-MAX_NUM_FORMS": 128,
        }
        self.login()

    def login(self):
        self.client.login(**self.credentials)

    def test_get(self):
        response = self.client.get(reverse("results_create_manual"))
        # initially there should be 16 results
        self.assertEqual(len(response.context["formset"]), 16)

    def test_upload_simple_result(self):
        self.client.post(reverse("results_create_manual"), self.data)

        results = Result.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].player.name, "Antoine Albertelli")
        self.assertEqual(results[0].ranking, 1)
        self.assertEqual(results[0].points, 10)
        self.assertEqual(results[0].win_count, 3)
        self.assertEqual(results[0].loss_count, 0)
        self.assertEqual(results[0].draw_count, 1)

    def test_import_garbage(self):
        self.data["form-0-points"] = "3@"
        resp = self.client.post(reverse("results_create_manual"), self.data)
        self.assertContains(resp, "Score should be in the win-loss")
        self.assertFalse(self.event.result_set.exists())

    def test_redirects_to_event_page(self):
        resp = self.client.post(reverse("results_create_manual"), self.data)
        self.assertRedirects(resp, self.event.get_absolute_url())

    def test_import_result_with_aliasing(self):
        orig_player = PlayerFactory(name="Test Player")
        PlayerAlias.objects.create(name="Antoine Albertelli", true_player=orig_player)

        self.client.post(reverse("results_create_manual"), self.data)
        results = Result.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].player.name, "Test Player")

    def test_import_double_space(self):
        self.data["form-0-name"] = "Antoine    Albertelli"
        self.client.post(reverse("results_create_manual"), self.data)

        results = Result.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].player.name, "Antoine Albertelli")

    def test_import_draws(self):
        self.data["form-0-points"] = "3-0-1"
        self.client.post(reverse("results_create_manual"), self.data)

        results = Result.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].points, 10)

    def test_import_more_than_one(self):
        self.data = {
            "form-0-name": "Antoine Albertelli",
            "form-0-points": "3-0",
            "form-1-name": "Bo Bobby",
            "form-1-points": "0-3",
            "form-2-name": "",
            "form-2-points": "",
            "event": self.event.id,
            "form-TOTAL_FORMS": 3,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 1,
            "form-MAX_NUM_FORMS": 128,
        }
        self.client.post(reverse("results_create_manual"), self.data)
        self.assertEqual(2, Result.objects.filter(event=self.event).count())

        names = [
            e.player.name
            for e in Result.objects.filter(event=self.event).order_by("ranking")
        ]
        self.assertEqual(names, ["Antoine Albertelli", "Bo Bobby"])

    def test_import_more_than_one_unsorted(self):
        """Checks that when importing players in an order not sorted by points,
        they are sorted before being given a ranking."""
        self.data = {
            "form-0-name": "Antoine",
            "form-0-points": "3-0",
            "form-1-name": "Bo",
            "form-1-points": "2-0",
            "form-2-name": "Charles",
            "form-2-points": "3-0",
            "form-3-name": "",
            "form-3-points": "",
            "event": self.event.id,
            "form-TOTAL_FORMS": 4,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 1,
            "form-MAX_NUM_FORMS": 128,
        }
        self.client.post(reverse("results_create_manual"), self.data)

        names = [
            e.player.name
            for e in Result.objects.filter(event=self.event).order_by("ranking")
        ]
        self.assertEqual(names, ["Antoine", "Charles", "Bo"])

    def test_tournament_validation(self):
        self.event.category = Event.Category.REGIONAL
        self.event.save()
        self.data["form-0-points"] = "5-0-1"
        resp = self.client.post(reverse("results_create_manual"), self.data)
        self.assertEqual(200, resp.status_code)
        self.assertContains(
            resp,
            "A SUL Regional event with 1 players should have at maximum 5 rounds.",
        )
        self.assertFalse(self.event.result_set.exists())

    def test_disable_tournament_validation(self):
        """Checks that we can override tournament validation.

        This feature is required for some very large events which have byes for
        select players, which for example result in too many points in total
        for the event.
        """
        # First create a large event with validation disabled
        self.event.category = Event.Category.REGIONAL
        self.event.results_validation_enabled = False
        self.event.save()

        # Then enter too many points
        self.data["form-0-points"] = "5-0-1"

        # And we should still have a succesful result
        self.client.post(reverse("results_create_manual"), self.data)
        self.assertTrue(self.event.result_set.exists(), "Should have accepted results")


class ImportSelectorTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.login()

    def login(self):
        self.client.login(**self.credentials)

    @parameterized.expand(
        [
            ("AETHERHUB", "results_create_aetherhub"),
            ("EVENTLINK", "results_create_eventlink"),
            ("MTGEVENT", "results_create_mtgevent"),
        ]
    )
    def test_selection_redirects(self, choice, view_name):
        data = {"site": choice}
        resp = self.client.post(reverse("results_create"), data, follow=True)
        self.assertRedirects(resp, reverse(view_name))


class FindEventsForUpload(TestCase):
    def test_find_events_for_upload(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        organizer = EventOrganizerFactory()
        event = RankedEventFactory(date=yesterday, organizer=organizer)

        self.assertIn(
            event, set(Event.objects.available_for_result_upload(organizer.user))
        )

    def test_old_events_not_shown(self):
        long_ago = datetime.date.today() - datetime.timedelta(days=100)
        organizer = EventOrganizerFactory()
        event = RankedEventFactory(date=long_ago, organizer=organizer)

        with self.settings(EVENT_MAX_AGE_FOR_RESULT_ENTRY=datetime.timedelta(30)):
            self.assertNotIn(
                event, Event.objects.available_for_result_upload(organizer.user)
            )

    def test_does_not_show_events_by_other_organizer(self):
        orga1 = EventOrganizerFactory()
        orga2 = EventOrganizerFactory()
        event = RankedEventFactory(date=datetime.date.today(), organizer=orga1)

        self.assertNotIn(event, Event.objects.available_for_result_upload(orga2.user))

    def test_does_not_show_events_with_results(self):
        event = RankedEventFactory(date=datetime.date.today())
        ResultFactory(event=event)
        self.assertNotIn(
            event, Event.objects.available_for_result_upload(event.organizer.user)
        )

    def test_does_not_show_future_events(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        event = RankedEventFactory(date=tomorrow)
        self.assertNotIn(
            event, Event.objects.available_for_result_upload(event.organizer.user)
        )

    def test_does_not_show_too_old_events(self):
        too_old_to_upload = datetime.date.today() - datetime.timedelta(days=32)
        event = RankedEventFactory(date=too_old_to_upload)
        self.assertNotIn(
            event,
            Event.objects.available_for_result_upload(event.organizer.user),
        )

    def test_edit_deadline_override(self):
        too_old_to_upload = datetime.date.today() - datetime.timedelta(days=32)
        event = RankedEventFactory(
            date=too_old_to_upload, edit_deadline_override=datetime.date.today()
        )
        self.assertIn(
            event,
            Event.objects.available_for_result_upload(event.organizer.user),
        )
        event.edit_deadline_override = datetime.date.today() - datetime.timedelta(
            days=1
        )
        event.save()
        self.assertNotIn(
            event,
            Event.objects.available_for_result_upload(event.organizer.user),
        )


class AddTop8Results(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = RankedEventFactory(
            organizer=self.organizer,
            date=datetime.date.today(),
        )

        self.winner = ResultFactory(event=self.event, ranking=3)
        self.finalist = ResultFactory(event=self.event, ranking=5)
        self.semi0 = ResultFactory(event=self.event, ranking=1)
        self.semi1 = ResultFactory(event=self.event, ranking=4)
        self.quarter0 = ResultFactory(event=self.event, ranking=2)
        self.quarter1 = ResultFactory(event=self.event, ranking=6)
        self.quarter2 = ResultFactory(event=self.event, ranking=7)
        self.quarter3 = ResultFactory(event=self.event, ranking=8)

        self.data = {
            "winner": self.winner.player.id,
            "finalist": self.finalist.player.id,
            "semi0": self.semi0.player.id,
            "semi1": self.semi1.player.id,
            "quarter0": self.quarter0.player.id,
            "quarter1": self.quarter1.player.id,
            "quarter2": self.quarter2.player.id,
            "quarter3": self.quarter3.player.id,
        }

        self.login()

    def login(self):
        self.client.login(**self.credentials)

    def test_redirects(self):
        resp = self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )

        self.assertRedirects(resp, reverse("event_details", args=(self.event.id,)))

    def test_update_player_result_top8(self):
        self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )

        self.assertEqual(
            Result.objects.get(id=self.winner.id).single_elimination_result,
            Result.SingleEliminationResult.WINNER,
        )
        self.assertEqual(
            Result.objects.get(id=self.finalist.id).single_elimination_result,
            Result.SingleEliminationResult.FINALIST,
        )
        self.assertEqual(
            Result.objects.get(id=self.semi0.id).single_elimination_result,
            Result.SingleEliminationResult.SEMI_FINALIST,
        )
        self.assertEqual(
            Result.objects.get(id=self.semi1.id).single_elimination_result,
            Result.SingleEliminationResult.SEMI_FINALIST,
        )
        self.assertEqual(
            Result.objects.get(id=self.quarter0.id).single_elimination_result,
            Result.SingleEliminationResult.QUARTER_FINALIST,
        )
        self.assertEqual(
            Result.objects.get(id=self.quarter1.id).single_elimination_result,
            Result.SingleEliminationResult.QUARTER_FINALIST,
        )
        self.assertEqual(
            Result.objects.get(id=self.quarter2.id).single_elimination_result,
            Result.SingleEliminationResult.QUARTER_FINALIST,
        )
        self.assertEqual(
            Result.objects.get(id=self.quarter3.id).single_elimination_result,
            Result.SingleEliminationResult.QUARTER_FINALIST,
        )

    def test_result_top8_not_allowed_for_other_users(self):
        # Change the owner of the event
        self.event.organizer = EventOrganizerFactory()
        self.event.save()
        resp = self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )
        self.assertEqual(404, resp.status_code)

    def test_result_top8_not_allowed_for_old_events(self):
        self.event.date = datetime.date.today() - datetime.timedelta(days=32)
        self.event.save()
        resp = self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
            follow=True,
        )
        self.assertRedirects(resp, reverse("event_details", args=(self.event.id,)))
        self.assertIsNone(
            Result.objects.get(id=self.winner.id).single_elimination_result
        )

    def test_result_top8_results_are_removed_before_upload(self):
        # first, post with initial data
        self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )

        # Create a new player, make it the winner
        new_winner = ResultFactory(event=self.event, ranking=2)
        self.data["winner"] = new_winner.id
        self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )

        # We should only have one winner and it should be the new one
        winners = self.event.result_set.filter(
            single_elimination_result=Result.SingleEliminationResult.WINNER
        )

        self.assertEqual(1, winners.count(), "Only one WINNER should be set.")
        self.assertEqual(new_winner, winners[0])

    def test_update_player_result_with_only_top4(self):
        # No quarterfinalist, only top4
        for i in range(4):
            del self.data[f"quarter{i}"]
        self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )

        # Check that we have one winner
        self.assertEqual(
            Result.objects.get(id=self.winner.id).single_elimination_result,
            Result.SingleEliminationResult.WINNER,
        )

        # And that we have no quarter finalist
        self.assertEqual(
            0,
            self.event.result_set.filter(
                single_elimination_result=Result.SingleEliminationResult.QUARTER_FINALIST
            ).count(),
        )

    def test_result_offer_only_top_players_as_choices(self):
        """
        Test that the top8 form only offers 9 options (8 players plus empty)
        for each result choice field.
        """
        event = RankedEventFactory()
        for i in range(1, 20):
            ResultFactory(event=event, ranking=i)
        form = AddTop8ResultsForm(event=event)
        for field in form.fields.values():
            if isinstance(field, AddTop8ResultsForm.ResultChoiceField):
                self.assertEqual(len(field.choices), 9)

    def test_must_play_top8_not_top4_if_big_enough(self):
        """Test that if we have more than 17 players, we are forced to enter a
        full top8 and not only top4, as suggested in MTR Appendix E."""
        for _ in range(9):
            ResultFactory(event=self.event)
        self.assertEqual(17, self.event.result_set.count())

        # play only top 4, which is not allowed with 17 players
        for i in range(4):
            del self.data[f"quarter{i}"]

        self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )

        self.assertFalse(
            self.event.result_set.filter(
                single_elimination_result=Result.SingleEliminationResult.WINNER
            ).exists(),
            "Should not have a winner.",
        )

    def test_duplicate_players(self):
        self.data["winner"] = self.data["finalist"]
        resp = self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )
        self.assertEqual(200, resp.status_code)
        self.assertFalse(
            self.event.result_set.filter(
                single_elimination_result=Result.SingleEliminationResult.WINNER
            ).exists(),
            "Should not have a winner.",
        )

    def test_odd_number_of_results(self):
        del self.data["quarter3"]
        resp = self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )
        self.assertEqual(200, resp.status_code)
        self.assertFalse(
            self.event.result_set.filter(
                single_elimination_result=Result.SingleEliminationResult.WINNER
            ).exists(),
            "Should not have a winner.",
        )
