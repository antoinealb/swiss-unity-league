import os.path

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from championship.models import EventPlayerResult
from championship.tests.parsers.utils import load_test_html
from championship.factories import *
from django.core.files.uploadedfile import SimpleUploadedFile
from championship.views import clean_name


from requests import HTTPError
from parameterized import parameterized


from unittest.mock import patch, MagicMock


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


class AetherhubImportTest(TestCase):
    """
    Tests for the feature that create new events for tournament organizers.
    """

    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = EventFactory(organizer=self.organizer, date=datetime.date.today())

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

        response = self.client.post(reverse("results_create_aetherhub"), self.data)

        results = EventPlayerResult.objects.filter(event=self.event).order_by("id")[:]

        # hardcoded spot checks from the tournament
        self.assertEqual(len(results), 30)
        self.assertEqual(results[0].points, 13)
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

        results = EventPlayerResult.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[1].player.name, "Test Player")

    @patch("requests.get")
    def test_imports_result_for_different_tourney_resuses_player(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        # Import the first event
        self.client.post(reverse("results_create_aetherhub"), self.data)

        # Create a second event, and import the results again
        second_event = EventFactory(
            organizer=self.organizer, date=datetime.date.today()
        )
        self.data["event"] = second_event.id
        self.client.post(reverse("results_create_aetherhub"), self.data)

        # Check that a random player has indeed two events to their name
        player = Player.objects.all()[0]
        results = EventPlayerResult.objects.filter(player=player).count()
        self.assertEqual(2, results, "Each player should have two results")

    @patch("requests.get")
    def test_imports_result_cleans_space_in_name(self, requests_get):
        self.login()
        self.mock_response(requests_get)

        # Import the first event
        self.client.post(reverse("results_create_aetherhub"), self.data)

        # This player in the mock result contains too many space between name
        # and first name
        player = Player.objects.get(name="Pavel Malach")

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

        # Try to import
        resp = self.client.post(reverse("results_create_aetherhub"), self.data)

        # Makes sure we return with an error
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Could not fetch standings", resp.content.decode())

    def test_only_allows_selection_of_events_with_no_results(self):
        """Checks that the user is only offered to upload results to
        tournaments that don't have results yet."""
        self.login()

        def _choices(response):
            choices = list(response.context["form"].fields["event"].choices)
            choices = [s[0].instance for s in choices[1:]]
            return choices

        # First, check that we have our event offered
        response = self.client.get(reverse("results_create_aetherhub"))
        gotChoices = _choices(response)
        wantChoices = [self.event]
        self.assertEqual(gotChoices, wantChoices)

        # Then create results for the event and makes sure we don't have the
        # event listed anymore
        EventPlayerResult.objects.create(
            points=10, player=PlayerFactory(), event=self.event, ranking=1
        )
        response = self.client.get(reverse("results_create_aetherhub"))
        gotChoices = _choices(response)
        self.assertEqual([], gotChoices)


class EventLinkImportTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = EventFactory(organizer=self.organizer, date=datetime.date.today())

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

        results = EventPlayerResult.objects.filter(event=self.event).order_by("id")[:]

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
        results = EventPlayerResult.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].player.name, "Test Player")

    def test_import_garbage(self):
        """Checks that when we try to import garbage data, we get a nice error
        message instead of a 500."""

        self.data["standings"] = SimpleUploadedFile(
            "standings", "FOOBAR".encode(), content_type="text/html"
        )

        self.login()
        resp = self.client.post(reverse("results_create_eventlink"), self.data)
        self.assertEqual(400, resp.status_code)
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
        EventPlayerResult.objects.create(
            points=10, player=PlayerFactory(), event=self.event, ranking=1
        )
        response = self.client.get(reverse("results_create_eventlink"))
        gotChoices = _choices(response)
        self.assertEqual([], gotChoices)


class ManualImportTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = EventFactory(organizer=self.organizer, date=datetime.date.today())

        self.data = {
            "form-0-name": "Antoine Albertelli",
            "form-0-points": "3-0",
            "event": self.event.id,
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 1,
            "form-MAX_NUM_FORMS": 128,
        }
        self.login()

    def login(self):
        self.client.login(**self.credentials)

    def test_upload_simple_result(self):
        self.client.post(reverse("results_create_manual"), self.data)

        results = EventPlayerResult.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].player.name, "Antoine Albertelli")
        self.assertEqual(results[0].ranking, 1)
        self.assertEqual(results[0].points, 9)

    def test_redirects_to_event_page(self):
        resp = self.client.post(reverse("results_create_manual"), self.data)
        self.assertRedirects(resp, self.event.get_absolute_url())

    def test_import_result_with_aliasing(self):
        orig_player = PlayerFactory(name="Test Player")
        PlayerAlias.objects.create(name="Antoine Albertelli", true_player=orig_player)

        self.client.post(reverse("results_create_manual"), self.data)
        results = EventPlayerResult.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].player.name, "Test Player")

    def test_import_double_space(self):
        self.data["form-0-name"] = "Antoine    Albertelli"
        self.client.post(reverse("results_create_manual"), self.data)

        results = EventPlayerResult.objects.filter(event=self.event).order_by("id")[:]
        self.assertEqual(results[0].player.name, "Antoine Albertelli")

    def test_import_draws(self):
        self.data["form-0-points"] = "3-0-1"
        self.client.post(reverse("results_create_manual"), self.data)

        results = EventPlayerResult.objects.filter(event=self.event).order_by("id")[:]
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
        self.assertEqual(2, EventPlayerResult.objects.filter(event=self.event).count())

        names = [
            e.player.name
            for e in EventPlayerResult.objects.filter(event=self.event).order_by(
                "ranking"
            )
        ]
        self.assertEqual(names, ["Antoine Albertelli", "Bo Bobby"])


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
        event = EventFactory(date=yesterday, organizer=organizer)

        self.assertIn(
            event, set(Event.objects.available_for_result_upload(organizer.user))
        )

    def test_old_events_not_shown(self):
        long_ago = datetime.date.today() - datetime.timedelta(days=100)
        organizer = EventOrganizerFactory()
        event = EventFactory(date=long_ago, organizer=organizer)

        with self.settings(EVENT_MAX_AGE_FOR_RESULT_ENTRY=datetime.timedelta(30)):
            self.assertNotIn(
                event, Event.objects.available_for_result_upload(organizer.user)
            )

    def test_does_not_show_events_by_other_organizer(self):
        orga1 = EventOrganizerFactory()
        orga2 = EventOrganizerFactory()
        event = EventFactory(date=datetime.date.today(), organizer=orga1)

        self.assertNotIn(event, Event.objects.available_for_result_upload(orga2.user))

    def test_does_not_show_events_with_results(self):
        event = EventFactory(date=datetime.date.today())
        EventPlayerResultFactory(event=event)
        self.assertNotIn(
            event, Event.objects.available_for_result_upload(event.organizer.user)
        )

    def test_does_not_show_future_events(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        event = EventFactory(date=tomorrow)
        self.assertNotIn(
            event, Event.objects.available_for_result_upload(event.organizer.user)
        )


class AddTop8Results(TestCase):
    def setUp(self):
        self.client = Client()
        self.credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(**self.credentials)
        self.organizer = EventOrganizerFactory(user=self.user)
        self.event = EventFactory(
            organizer=self.organizer, category=Event.Category.REGIONAL
        )

        self.winner = EventPlayerResultFactory(event=self.event)
        self.finalist = EventPlayerResultFactory(event=self.event)
        self.semi0 = EventPlayerResultFactory(event=self.event)
        self.semi1 = EventPlayerResultFactory(event=self.event)
        self.quarter0 = EventPlayerResultFactory(event=self.event)
        self.quarter1 = EventPlayerResultFactory(event=self.event)
        self.quarter2 = EventPlayerResultFactory(event=self.event)
        self.quarter3 = EventPlayerResultFactory(event=self.event)

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
            EventPlayerResult.objects.get(id=self.winner.id).single_elimination_result,
            EventPlayerResult.SingleEliminationResult.WINNER,
        )
        self.assertEqual(
            EventPlayerResult.objects.get(
                id=self.finalist.id
            ).single_elimination_result,
            EventPlayerResult.SingleEliminationResult.FINALIST,
        )
        self.assertEqual(
            EventPlayerResult.objects.get(id=self.semi0.id).single_elimination_result,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST,
        )
        self.assertEqual(
            EventPlayerResult.objects.get(id=self.semi1.id).single_elimination_result,
            EventPlayerResult.SingleEliminationResult.SEMI_FINALIST,
        )
        self.assertEqual(
            EventPlayerResult.objects.get(
                id=self.quarter0.id
            ).single_elimination_result,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
        )
        self.assertEqual(
            EventPlayerResult.objects.get(
                id=self.quarter1.id
            ).single_elimination_result,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
        )
        self.assertEqual(
            EventPlayerResult.objects.get(
                id=self.quarter2.id
            ).single_elimination_result,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
        )
        self.assertEqual(
            EventPlayerResult.objects.get(
                id=self.quarter3.id
            ).single_elimination_result,
            EventPlayerResult.SingleEliminationResult.QUARTER_FINALIST,
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

    def test_result_top8_not_allowed_for_regular_events(self):
        self.event.category = Event.Category.REGULAR
        self.event.save()
        resp = self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
            follow=True,
        )
        self.assertRedirects(resp, reverse("event_details", args=(self.event.id,)))
        self.assertIn("Top 8 are not allowed at SUL Regular.", resp.content.decode())
        self.assertIsNone(
            EventPlayerResult.objects.get(id=self.winner.id).single_elimination_result
        )

    def test_result_top8_results_are_removed_before_upload(self):
        # first, post with initial data
        resp = self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )

        # Create a new player, make it the winner
        new_winner = EventPlayerResultFactory(event=self.event)
        self.data["winner"] = new_winner.id
        resp = self.client.post(
            reverse("results_top8_add", args=(self.event.id,)),
            data=self.data,
        )

        # We should only have one winner and it should be the new one
        winners = self.event.eventplayerresult_set.filter(
            single_elimination_result=EventPlayerResult.SingleEliminationResult.WINNER
        )

        self.assertEqual(1, winners.count(), "Only one WINNER should be set.")
        self.assertEqual(new_winner, winners[0])
