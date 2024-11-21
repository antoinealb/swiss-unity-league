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


from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK

from decklists.factories import DecklistFactory
from oracle.factories import CardFactory


class DecklistViewTestCase(TestCase):
    databases = ["oracle", "default"]

    def setUp(self):
        self.mother = CardFactory(
            mana_value=1, type_line="Creature — Human Cleric", name="Mother of Runes"
        )
        self.stoneforge = CardFactory(
            mana_value=2, type_line="Creature — Kor Artificer", name="Stoneforge Mystic"
        )
        self.plains = CardFactory(mana_value=0, type_line="Basic Land", name="Plains")
        self.path = CardFactory(mana_value=1, type_line="Instant", name="Path to Exile")

    def test_can_get_decklist(self):
        decklist = DecklistFactory(archetype="Burn")
        resp = self.client.get(reverse("decklist-details", args=[decklist.id]))
        self.assertEqual(HTTP_200_OK, resp.status_code)
        self.assertIn(decklist.player.name, resp.content.decode())
        self.assertIn(decklist.archetype, resp.content.decode())

    def test_link_edit_decklist_if_before_deadline(self):
        decklist = DecklistFactory()
        url = reverse("decklist-update", args=[decklist.id])
        resp = self.client.get(reverse("decklist-details", args=[decklist.id]))
        self.assertIn(url, resp.content.decode())

    def test_nolink_edit_decklist_after_deadline(self):
        decklist = DecklistFactory(collection__published=True)
        url = reverse("decklist-update", args=[decklist.id])
        resp = self.client.get(reverse("decklist-details", args=[decklist.id]))
        self.assertNotIn(url, resp.content.decode())

    def test_link_edit_decklist_after_deadline_for_organizer(self):
        decklist = DecklistFactory(collection__published=True)
        self.client.force_login(decklist.collection.event.organizer.user)
        url = reverse("decklist-update", args=[decklist.id])
        resp = self.client.get(reverse("decklist-details", args=[decklist.id]))
        self.assertIn(url, resp.content.decode())

    def test_section_card_counter(self):
        decklist = DecklistFactory(archetype="Burn")
        decklist.mainboard = f"4 {self.stoneforge.name}\n3{self.plains.name}"
        decklist.sideboard = f"2 {self.path.name}"
        decklist.save()

        resp = self.client.get(reverse("decklist-details", args=[decklist.id]))
        self.assertContains(resp, "Creatures (4)")
        self.assertContains(resp, "Lands (3)")
        self.assertContains(resp, "Sideboard (2)")
        self.assertContains(resp, "Total Cards: 9")

    def test_inside_section_cards_are_sorted_by_mana_value(self):
        decklist = DecklistFactory(
            mainboard=f"4 {self.stoneforge.name}\n4 {self.mother.name}"
        )
        resp = self.client.get(reverse("decklist-details", args=[decklist.id]))
        want = [self.mother.name, self.stoneforge.name]
        got = [c.name for c in resp.context["cards_by_section"]["Creatures (8)"]]
        self.assertEqual(want, got)

    def test_unknown_card_section(self):
        decklist = DecklistFactory(mainboard="4 Fooburb")
        resp = self.client.get(reverse("decklist-details", args=[decklist.id]))
        self.assertEqual(
            resp.context["cards_by_section"]["Unknown (4)"][0].name, "Fooburb"
        )

    def test_no_card_sections_if_using_sharing_key(self):
        """
        Check that we can sort by mana value instead of the default mode.
        """
        decklist = DecklistFactory(
            mainboard=f"4 {self.stoneforge.name}\n4 {self.path.name}",
            sideboard=f"4 {self.mother.name}",
        )
        resp = self.client.get(
            reverse("decklist-details", args=[decklist.id]) + "?sort=manavalue"
        )
        want_mainboard = [self.path.name, self.stoneforge.name]
        got_mainboard = [
            c.name for c in resp.context["cards_by_section"]["Mainboard (8)"]
        ]
        self.assertEqual(got_mainboard, want_mainboard)
        want_sideboard = [self.mother.name]
        got_sideboard = [
            c.name for c in resp.context["cards_by_section"]["Sideboard (4)"]
        ]
        self.assertEqual(got_sideboard, want_sideboard)
