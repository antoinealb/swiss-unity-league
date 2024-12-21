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

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from freezegun import freeze_time
from parameterized import parameterized

from championship.factories import (
    EventFactory,
    EventOrganizerFactory,
    OldCategoryRankedEventFactory,
    RecurringEventFactory,
    ResultFactory,
)
from championship.models import Event, Result
from multisite.constants import GLOBAL_DOMAIN
from multisite.tests.utils import with_site


class EventDetailTestCase(TestCase):
    """
    Tests how we can get an event's detail page.
    """

    def setUp(self):
        self.client = Client()
        credentials = dict(username="test", password="test")
        self.user = User.objects.create_user(is_staff=True, **credentials)
        self.user.user_permissions.add(Permission.objects.get(codename="change_event"))
        self.user.save()
        self.client.login(**credentials)

    def test_get_page(self):
        event = EventFactory(category=Event.Category.PREMIER)
        ep = ResultFactory(
            points=10,
            event=event,
            ranking=1,
            win_count=3,
            loss_count=0,
            draw_count=1,
        )

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertIn(event.name, resp.content.decode())
        self.assertIn(ep.player.name, resp.content.decode())

        scores = [s for _, s in resp.context_data["results"]]
        results = [r for r, _ in resp.context_data["results"]]

        self.assertEqual(results[0].points, 10)
        self.assertEqual(scores[0].qps, (10 + 3) * 6)
        self.assertContains(resp, "League Points")

    def test_get_result_with_top_8(self):
        category = Event.Category.PREMIER
        event = EventFactory(category=category)

        # Create 18 results with a top8
        results = (
            [
                Result.PlayoffResult.WINNER,
                Result.PlayoffResult.FINALIST,
            ]
            + [Result.PlayoffResult.SEMI_FINALIST] * 2
            + [Result.PlayoffResult.QUARTER_FINALIST] * 4
            + [None] * 10  # outside of top8
        )

        for i, r in enumerate(results):
            ResultFactory(
                event=event,
                ranking=i + 1,
                playoff_result=r,
                points=9,
                win_count=3,
                loss_count=0,
                draw_count=0,
            )

        resp = self.client.get(reverse("event_details", args=[event.id]))
        results = [r for r, _ in resp.context_data["results"]]
        self.assertEqual(results[8].ranking, 9)
        self.assertEqual(
            results[0].playoff_result,
            Result.PlayoffResult.WINNER,
        )
        self.assertEqual(
            results[0].get_ranking_display(),
            "1st",
        )
        self.assertEqual(
            results[8].get_ranking_display(),
            "9th",
        )

    def test_results_category_others_shows_no_points(self):
        """
        Checks that SUL Other events can have results but should not display any SUL points.
        """
        result = ResultFactory(event__category=Event.Category.OTHER)
        resp = self.client.get(reverse("event_details", args=[result.event.id]))
        self.assertEqual(resp.context["results"][0][0], result)
        self.assertIsNone(resp.context["results"][0][1], "score should be none")
        self.assertNotContains(resp, "League Points")

    def test_escapes_content_description(self):
        """
        Checks that we correctly strip tags unknown tags.
        """
        descr = """
        <b>Bold</b>
        <script>alert()</script>
        """
        want = """
        <b>Bold</b>
        alert()
        """
        event = EventFactory(description=descr)
        self.assertEqual(want, event.description)

    def test_shows_link_for_admin_page(self):
        event = EventFactory()
        resp = self.client.get(reverse("event_details", args=[event.id]))

        self.assertIn(
            reverse("admin:championship_event_change", args=[event.id]),
            resp.content.decode(),
        )

    def test_link_is_hidden_for_staff_users_without_permission(self):
        event = EventFactory()
        self.user.user_permissions.clear()
        self.user.save()

        resp = self.client.get(event.get_absolute_url())
        self.assertNotIn(
            reverse("admin:championship_event_change", args=[event.id]),
            resp.content.decode(),
        )

    def test_shows_link_edit_all_recurring_events(self):
        """If the event is a recurring event, we should show a link to the TO to edit all events of the series."""
        event = EventFactory(
            recurring_event=RecurringEventFactory(),
            organizer=EventOrganizerFactory(user=self.user),
            date=datetime.date.today(),
        )
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(resp, reverse("event_update_all", args=[event.id]))

    def test_hides_link_for_top8_if_no_results(self):
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(
            category=Event.Category.REGIONAL,
            organizer=organizer,
            date=datetime.date.today(),
        )

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertNotContains(
            resp,
            reverse("results_top8_add", args=[event.id]),
        )

    def test_shows_link_for_top8(self):
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(
            category=Event.Category.REGIONAL,
            organizer=organizer,
            date=datetime.date.today(),
        )
        # Result is needed to show the link
        ResultFactory(event=event)

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(
            resp,
            reverse("results_top8_add", args=[event.id]),
        )

    def test_shows_no_link_for_top8_old_events(self):
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(
            category=Event.Category.REGIONAL,
            organizer=organizer,
            date=datetime.date.today() - datetime.timedelta(32),
        )

        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertNotContains(
            resp,
            reverse("results_top8_add", args=[event.id]),
        )

    def test_shows_no_link_top8_regular(self):
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(
            category=Event.Category.REGULAR,
            organizer=organizer,
            date=datetime.date.today(),
        )
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertNotIn(
            reverse("results_top8_add", args=[event.id]),
            resp.content.decode(),
        )

    def test_shows_link_update_recurring_event(self):
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(
            organizer=organizer,
            date=datetime.date.today(),
            recurring_event=RecurringEventFactory(),
        )
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertNotContains(
            resp,
            reverse("recurring_event_create", args=[event.id]),
        )
        self.assertContains(
            resp,
            reverse("event_update_all", args=[event.id]),
        )
        self.assertContains(
            resp,
            reverse("recurring_event_update", args=[event.recurring_event_id]),
        )

    def test_shows_event_series(self):
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(
            organizer=organizer,
            recurring_event=RecurringEventFactory(),
        )
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(
            resp,
            event.recurring_event.name,
        )

    def test_shows_link_delete_results(self):
        yesterday = datetime.date.today() - datetime.timedelta(1)
        organizer = EventOrganizerFactory(user=self.user)
        event = EventFactory(
            category=Event.Category.REGULAR, organizer=organizer, date=yesterday
        )
        for _ in range(3):
            ResultFactory(event=event)
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertIn(
            reverse("event_clear_results", args=[event.id]),
            resp.content.decode(),
        )

    def test_shows_link_to_player_details(self):
        result = ResultFactory()
        resp = self.client.get(reverse("event_details", args=[result.event.id]))
        self.assertIn(
            reverse("player_details", args=[result.player.id]), resp.content.decode()
        )

    def test_skips_links_if_hidden(self):
        result = ResultFactory(
            player__name="Test Player",
        )
        result.player.hidden_from_leaderboard = True
        result.player.save()
        resp = self.client.get(reverse("event_details", args=[result.event.id]))
        self.assertNotIn(
            reverse("player_details", args=[result.player.id]), resp.content.decode()
        )

        # The last name should be replaced by initials
        self.assertIn("Test P.", resp.content.decode())

    def test_shows_record(self):
        event = OldCategoryRankedEventFactory()
        ResultFactory(
            event=event,
            win_count=3,
            loss_count=1,
            draw_count=1,
        )
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(resp, "3 - 1 - 1")

    @parameterized.expand(
        [
            (datetime.timedelta(32), False),
            (datetime.timedelta(31), True),
            (datetime.timedelta(5), True),
            (datetime.timedelta(4), False),
            (datetime.timedelta(0), False),
        ]
    )
    def test_missing_results_info(self, minus_delta, missing_results_info_expected):
        with freeze_time("2024-06-01"):
            event = EventFactory(
                category=Event.Category.REGULAR,
                date=datetime.date.today() - minus_delta,
            )
            resp = self.client.get(reverse("event_details", args=[event.id]))
            self.assertEqual(
                missing_results_info_expected,
                resp.context_data["notify_missing_results"],
                msg=minus_delta,
            )

    def test_shows_time_with_title(self):
        event = EventFactory()
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(resp, "Date")
        self.assertNotContains(resp, "Date & Time")

        event.start_time = datetime.time(10, 0)
        event.end_time = datetime.time(19, 0)
        event.save()
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(resp, "10:00 - 19:00")
        self.assertContains(resp, "Date & Time")

    @parameterized.expand(
        [
            (Event.Category.REGULAR, True),
            (Event.Category.REGIONAL, True),
            (Event.Category.PREMIER, False),
        ]
    )
    def test_shows_link_to_schedule_event_series(self, category, show_link):
        event = EventFactory(category=category)
        self.client.force_login(event.organizer.user)
        resp = self.client.get(reverse("event_details", args=[event.id]))
        if show_link:
            self.assertContains(
                resp,
                reverse("recurring_event_create", args=[event.id]),
            )
        else:
            self.assertNotContains(
                resp,
                reverse("recurring_event_create", args=[event.id]),
            )

    @with_site(GLOBAL_DOMAIN)
    def test_premier_shows_as_regional(self):
        event = EventFactory(category=Event.Category.PREMIER)
        resp = self.client.get(reverse("event_details", args=[event.id]))
        self.assertContains(resp, Event.Category.REGIONAL.label)


class EventImageValidation(TestCase):

    def test_image_validation_file_type(self):
        valid_image = SimpleUploadedFile(
            "valid_image.jpg", b"file_content", content_type="image/jpeg"
        )
        invalid_image = SimpleUploadedFile(
            "invalid_image.txt", b"file_content", content_type="text/plain"
        )
        event = EventFactory()
        event.image = invalid_image
        with self.assertRaises(ValidationError):
            event.full_clean()
        event.image = valid_image
        event.full_clean()

    def test_image_validation_size(self):
        valid_image = SimpleUploadedFile(
            "valid_image.jpg", b"file_content", content_type="image/jpeg"
        )
        invalid_image = SimpleUploadedFile(
            "invalid_image.jpg", b"a" * 2 * 1024**2, content_type="image/jpeg"
        )
        event = EventFactory()
        event.image = invalid_image
        with self.assertRaises(ValidationError):
            event.full_clean()
        event.image = valid_image
        event.full_clean()
