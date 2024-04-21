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

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.status import HTTP_200_OK

from decklists.factories import CollectionFactory, DecklistFactory


class DecklistViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()

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
        deadline = timezone.now() - timezone.timedelta(seconds=1)
        collection = CollectionFactory(submission_deadline=deadline)
        decklist = DecklistFactory(collection=collection)
        url = reverse("decklist-update", args=[decklist.id])
        resp = self.client.get(reverse("decklist-details", args=[decklist.id]))
        self.assertNotIn(url, resp.content.decode())
