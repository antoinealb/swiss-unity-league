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

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from freezegun import freeze_time
from parameterized import parameterized

from championship.factories import (
    EventFactory,
    EventOrganizerFactory,
    OrganizerLeagueFactory,
    RecurringEventFactory,
    ResultFactory,
)
from championship.models import Event, OrganizerLeague
from championship.season import SEASON_LIST
from championship.views.organizers import ORGANIZER_LEAGUE_DESCRIPTION
from multisite.factories import SiteFactory


class EventOrganizerDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = EventOrganizerFactory()
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        past_date = datetime.date.today() - datetime.timedelta(days=5)

        self.future_event = EventFactory(organizer=self.organizer, date=tomorrow)
        self.past_event = EventFactory(organizer=self.organizer, date=past_date)
        self.response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )

    def test_organizer_detail_view(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertTemplateUsed(self.response, "championship/organizer_details.html")
        self.assertContains(self.response, self.organizer.name)
        self.assertContains(self.response, self.future_event.name)
        self.assertContains(self.response, self.past_event.name)

    def test_organizer_detail_future_and_past(self):
        self.assertTrue("all_events" in self.response.context)
        self.assertEqual(len(self.response.context["all_events"]), 2)
        # Test Future Events
        self.assertEqual(
            self.response.context["all_events"][0]["list"][0], self.future_event
        )
        # Test Past Events
        self.assertEqual(
            self.response.context["all_events"][1]["list"][0], self.past_event
        )

    def test_past_events_contain_num_of_participants(self):
        ResultFactory(event=self.past_event)
        self.response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        response_past_event = self.response.context["all_events"][1]
        self.assertEqual(response_past_event["has_num_players"], True)
        first_event = response_past_event["list"][0]
        self.assertEqual(first_event.num_players, 1)

    def test_organizer_detail_view_no_organizer(self):
        self.response = self.client.get(
            reverse("organizer_details", args=[9999])
        )  # assuming 9999 is an invalid ID
        self.assertEqual(self.response.status_code, 404)

    def test_organizer_reverse(self):
        self.client.force_login(self.organizer.user)
        edit_organizer_url = reverse("organizer_update")
        self.response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        self.assertContains(self.response, f'href="{edit_organizer_url}"')

    def test_recurring_events_shown(self):
        recurring_event = RecurringEventFactory(end_date=datetime.date.today())
        self.future_event.recurring_event = recurring_event
        self.future_event.save()
        response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        recurring_events = response.context["recurring_events"]
        self.assertEqual(len(recurring_events), 1)
        self.assertEqual(recurring_events[0], recurring_event)
        self.assertContains(response, "Active Event Series")

    def test_no_table_shown_without_active_recurring_event(self):
        self.assertNotContains(self.response, "Active Event Series")
        recurring_event = RecurringEventFactory(
            end_date=datetime.date.today() - timezone.timedelta(days=1)
        )
        self.past_event.recurring_event = recurring_event
        self.past_event.save()
        response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        self.assertNotContains(response, "Active Event Series")

    def test_recurring_events_ordered_by_start_date(self):
        recurring_event1 = RecurringEventFactory(
            start_date=datetime.date.today(), end_date=datetime.date.today()
        )
        recurring_event2 = RecurringEventFactory(
            start_date=datetime.date.today() + timezone.timedelta(days=1),
            end_date=datetime.date.today(),
        )
        EventFactory(organizer=self.organizer, recurring_event=recurring_event1)
        EventFactory(organizer=self.organizer, recurring_event=recurring_event2)
        response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        recurring_events = response.context["recurring_events"]
        self.assertEqual(len(recurring_events), 2)
        self.assertEqual(recurring_events[0], recurring_event1)
        self.assertEqual(recurring_events[1], recurring_event2)

    def test_edit_recurring_event_only_shown_to_organizer(self):
        recurring_event = RecurringEventFactory()
        self.future_event.recurring_event = recurring_event
        self.future_event.save()
        response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        self.assertNotContains(
            response, reverse("recurring_event_update", args=[recurring_event.id])
        )
        self.client.force_login(self.organizer.user)
        response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        self.assertContains(
            response, reverse("recurring_event_update", args=[recurring_event.id])
        )

    def test_shows_event_formats(self):
        self.response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        self.assertContains(self.response, self.future_event.get_format_display())
        self.assertContains(self.response, self.past_event.get_format_display())

    def test_shows_correct_date_format(self):
        self.past_event.date = datetime.date(2024, 11, 1)
        self.past_event.save()
        self.response = self.client.get(
            reverse("organizer_details", args=[self.organizer.id])
        )
        self.assertContains(self.response, "Fri, 01.11.2024")


class OrganizerImageValidation(TestCase):

    def test_image_validation_file_type(self):
        valid_image = SimpleUploadedFile(
            "valid_image.jpg", b"file_content", content_type="image/jpeg"
        )
        invalid_image = SimpleUploadedFile(
            "invalid_image.txt", b"file_content", content_type="text/plain"
        )
        organizer = EventOrganizerFactory()
        organizer.image = invalid_image
        with self.assertRaises(ValidationError):
            organizer.full_clean()
        organizer.image = valid_image
        organizer.full_clean()

    def test_image_validation_size(self):
        valid_image = SimpleUploadedFile(
            "valid_image.jpg", b"file_content", content_type="image/jpeg"
        )
        invalid_image = SimpleUploadedFile(
            "invalid_image.jpg", b"a" * 501 * 1024, content_type="image/jpeg"
        )
        organizer = EventOrganizerFactory()
        organizer.image = invalid_image
        with self.assertRaises(ValidationError):
            organizer.full_clean()
        organizer.image = valid_image
        organizer.full_clean()


class OrganizerListViewTest(TestCase):
    def test_organizer_view(self):
        event = EventFactory()
        response = self.client.get(reverse("organizer_view"))
        self.assertContains(response, event.organizer.name)
        self.assertContains(
            response,
            event.organizer.default_address.city,
            msg_prefix="response should contain city of the organizer",
        )

    def test_organizer_without_events_is_skipped(self):
        to_without_event = EventOrganizerFactory()
        response = self.client.get(reverse("organizer_view"))
        self.assertNotContains(response, to_without_event.name)

    def test_organizer_on_another_site_is_skipped(self):
        event = EventFactory(organizer__site=SiteFactory())
        response = self.client.get(reverse("organizer_view"))
        self.assertNotContains(response, event.organizer.name)


class OrganizerLeaderboardTest(TestCase):

    @parameterized.expand(SEASON_LIST)
    def test_organizer_ranking_for_season(self, season):
        with freeze_time(season.end_date + datetime.timedelta(days=1)):
            organizer = EventOrganizerFactory()
            # Check that it's possible to fetch the organizer details even though ther are no results
            response = self.client.get(
                reverse("organizer_details", args=[organizer.id])
            )
            for i in range(3):
                ResultFactory(
                    event__organizer=organizer,
                    event__category=Event.Category.REGULAR,
                    event__date=season.start_date + datetime.timedelta(days=i),
                    win_count=i + 1,
                    draw_count=0,
                    loss_count=0,
                )

            response = self.client.get(
                reverse("organizer_details", args=[organizer.id])
            )
            self.assertTrue("players" in response.context)
            self.assertEqual(len(response.context["players"]), 3)
            self.assertEqual(response.context["players"][0].score.rank, 1)
            self.assertContains(
                response,
                ORGANIZER_LEAGUE_DESCRIPTION.format(
                    organizer_name=organizer.name, season_name=season.name
                ),
            )

    def test_organizer_league_leaderboard(self):
        league = OrganizerLeagueFactory(
            format=OrganizerLeague.Format.All_FORMATS,
            category=Event.Category.REGIONAL,
            end_date=datetime.date.today(),
        )
        result = ResultFactory(
            event__organizer=league.organizer,
            event__category=Event.Category.REGULAR,
        )

        resp = self.client.get(reverse("organizer_details", args=[league.organizer_id]))

        self.assertContains(resp, league.name)
        self.assertContains(resp, league.get_format_display())
        self.assertContains(resp, "SUL Regular and SUL Regional")
        if not league.playoffs:
            self.assertContains(resp, "without playoffs")
        self.assertContains(resp, result.player.name)
