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

from django.core.management import call_command
from django.test import TestCase

from waffle.testutils import override_sample

from championship.factories import (
    AddressFactory,
    EventOrganizerFactory,
    PlayerFactory,
    ResultFactory,
)
from championship.management.commands.assign_countries_to_players import (
    assign_country_to_player,
)
from championship.models import Event, PlayerSeasonData
from championship.seasons.definitions import EU_SEASON_2025
from multisite.constants import SWISS_DOMAIN
from multisite.tests.utils import with_site


class AssignCountryToPlayerTest(TestCase):
    def setUp(self):
        self.player = PlayerFactory()

    def test_country_assigned_to_player(self):
        result = ResultFactory(
            event__season=EU_SEASON_2025,
            event__excluded_categories=[Event.Category.GRAND_PRIX],
            player=self.player,
        )

        assign_country_to_player(self.player, EU_SEASON_2025)
        season_data = PlayerSeasonData.objects.get(player=self.player)
        self.assertEqual(
            season_data.country, result.event.organizer.default_address.country
        )
        self.assertEqual(season_data.season_slug, EU_SEASON_2025.slug)
        self.assertTrue(season_data.auto_assign_country)

    def test_player_without_events_no_country_assigned(self):
        assign_country_to_player(self.player, EU_SEASON_2025)
        self.assertFalse(PlayerSeasonData.objects.filter(player=self.player).exists())

    def test_grand_prix_event_ignored(self):
        ResultFactory(
            event__season=EU_SEASON_2025,
            event__category=Event.Category.GRAND_PRIX,
            player=self.player,
        )
        assign_country_to_player(self.player, EU_SEASON_2025)
        self.assertFalse(PlayerSeasonData.objects.filter(player=self.player).exists())

    def test_most_frequent_country_assigned(self):
        ResultFactory.create_batch(
            2,
            event__season=EU_SEASON_2025,
            event__excluded_categories=[Event.Category.GRAND_PRIX],
            player=self.player,
        )
        most_frequent_organizer = EventOrganizerFactory()
        ResultFactory.create_batch(
            3,
            event__season=EU_SEASON_2025,
            event__excluded_categories=[Event.Category.GRAND_PRIX],
            player=self.player,
            event__organizer=most_frequent_organizer,
        )

        assign_country_to_player(self.player, EU_SEASON_2025)
        self.assertEqual(
            PlayerSeasonData.objects.get(player=self.player).country,
            most_frequent_organizer.default_address.country,
        )

    def test_override_assigned_country(self):
        result = ResultFactory(
            event__season=EU_SEASON_2025,
            event__excluded_categories=[Event.Category.GRAND_PRIX],
            player=self.player,
        )
        assign_country_to_player(self.player, EU_SEASON_2025)
        self.assertEqual(
            PlayerSeasonData.objects.get(player=self.player).country,
            result.event.organizer.default_address.country,
        )
        self.assertEqual(PlayerSeasonData.objects.all().count(), 1)

        most_frequent_organizer = EventOrganizerFactory()
        ResultFactory.create_batch(
            2,
            event__season=EU_SEASON_2025,
            event__excluded_categories=[Event.Category.GRAND_PRIX],
            player=self.player,
            event__organizer=most_frequent_organizer,
        )
        assign_country_to_player(self.player, EU_SEASON_2025)
        self.assertEqual(
            PlayerSeasonData.objects.get(player=self.player).country,
            most_frequent_organizer.default_address.country,
        )
        self.assertEqual(PlayerSeasonData.objects.all().count(), 1)

    def test_event_address_prioritized_over_organizer_address(self):
        organizer = EventOrganizerFactory()
        result = ResultFactory(
            event__season=EU_SEASON_2025,
            event__excluded_categories=Event.Category.GRAND_PRIX,
            player=self.player,
            event__organizer=organizer,
            event__address=AddressFactory(organizer=organizer),
        )

        assign_country_to_player(self.player, EU_SEASON_2025)
        season_data = PlayerSeasonData.objects.get(player=self.player)
        self.assertEqual(season_data.country, result.event.address.country)


@with_site(EU_SEASON_2025.domain)
@override_sample("assign_countries_to_player_fraction", active=True)
class AssignCountriesToAllPlayersTest(TestCase):

    def test_assign_countries_to_all_players(self):
        ResultFactory.create_batch(
            2,
            event__season=EU_SEASON_2025,
            event__excluded_categories=[Event.Category.GRAND_PRIX],
        )
        call_command("assign_countries_to_players", season=EU_SEASON_2025.slug)
        self.assertEqual(2, PlayerSeasonData.objects.all().count())

    def test_disable_auto_assign_country(self):
        result = ResultFactory(
            event__season=EU_SEASON_2025,
            event__excluded_categories=[Event.Category.GRAND_PRIX],
        )
        PlayerSeasonData.objects.create(
            player=result.player,
            season_slug=EU_SEASON_2025.slug,
            country="CH",
            auto_assign_country=False,
        )

        # Make sure player played more events in a different country
        most_frequent_organizer = EventOrganizerFactory()
        ResultFactory.create_batch(
            2,
            event__season=EU_SEASON_2025,
            event__excluded_categories=[Event.Category.GRAND_PRIX],
            player=result.player,
            event__organizer=most_frequent_organizer,
        )

        # Check that country is not overriden due to auto_assign_country = False
        call_command("assign_countries_to_players", season=EU_SEASON_2025.slug)
        self.assertEqual(
            PlayerSeasonData.objects.get(player=result.player).country, "CH"
        )
        self.assertEqual(PlayerSeasonData.objects.all().count(), 1)

    def test_disable_auto_assign_country_not_affect_other_seasons(self):
        result = ResultFactory(
            event__season=EU_SEASON_2025,
            event__excluded_categories=[Event.Category.GRAND_PRIX],
        )
        PlayerSeasonData.objects.create(
            player=result.player,
            season_slug="otherseasonslug",
            country="CH",
            auto_assign_country=True,
        )

        call_command("assign_countries_to_players", season=EU_SEASON_2025.slug)
        self.assertEqual(
            PlayerSeasonData.objects.get(
                player=result.player, season_slug=EU_SEASON_2025.slug
            ).country,
            result.event.organizer.default_address.country,
        )
        self.assertEqual(PlayerSeasonData.objects.all().count(), 2)

    @with_site(SWISS_DOMAIN)
    def test_eu_season_only(self):
        with self.assertRaises(KeyError):
            call_command("assign_countries_to_players")
