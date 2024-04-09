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

from django.test import TestCase
from django.utils.timezone import now

from championship.factories import EventFactory, EventOrganizerFactory, PlayerFactory
from decklists.factories import CollectionFactory, DecklistFactory
from decklists.models import Collection, Decklist


class CollectionTest(TestCase):
    def test_str(self):
        eo = EventOrganizerFactory(name="Leonin League")
        event = EventFactory(organizer=eo)
        collection = Collection(
            name="Foobar",
            submission_deadline=datetime.datetime.now(),
            event=event,
        )

        want = "Foobar (by Leonin League)"
        self.assertEqual(str(collection), want)

    def test_factory(self):
        collection = CollectionFactory()
        self.assertIn(collection.event.organizer.name, str(collection))

    def test_published(self):
        collection = CollectionFactory()
        self.assertFalse(collection.decklists_published)

        collection = CollectionFactory(
            publication_time=now() - datetime.timedelta(hours=1)
        )
        self.assertTrue(collection.decklists_published)


class DecklistTest(TestCase):
    def test_str(self):
        player = PlayerFactory(name="Antoine Albertelli")
        decklist = DecklistFactory(player=player, archetype="Burn")

        want = "Antoine Albertelli (Burn)"
        self.assertEqual(str(decklist), want)

    def test_factory(self):
        dl = DecklistFactory()
        self.assertIsNotNone(dl.id)

    def test_decklists_ids_are_all_unique(self):
        n = 10
        collection = CollectionFactory()
        player = PlayerFactory()
        ids = set(
            DecklistFactory(collection=collection, player=player).id for _ in range(n)
        )
        self.assertEqual(n, len(ids))

    def test_can_be_edited_if_before_deadline(self):
        decklist = DecklistFactory()
        self.assertTrue(decklist.can_be_edited())

    def test_can_not_be_edited_if_after(self):
        decklist = DecklistFactory()
        decklist.collection.submission_deadline -= datetime.timedelta(days=200)
        self.assertFalse(decklist.can_be_edited())
