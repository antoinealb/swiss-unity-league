
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.status import HTTP_200_OK

from championship.factories import EventFactory, PlayerFactory, ResultFactory
from decklists.factories import CollectionFactory, DecklistFactory
from oracle.factories import CardFactory


class DecklistViewTestCase(TestCase):
    databases = ["oracle", "default"]

    def setUp(self):
        self.result = ResultFactory()
        self.player = self.result.player
        self.event = self.result.event

    def test_can_get_decklists(self):
        player = ResultFactory(event=self.event).player
        decklist1 = DecklistFactory(player=player, collection__event=self.event)
        decklist2 = DecklistFactory(player=player, collection__event=self.event)
        decklist1 = DecklistFactory(player=self.player, collection__event=self.event)
        decklist2 = DecklistFactory(player=self.player, collection__event=self.event)
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(resp, decklist1.archetype)
        self.assertContains(resp, decklist1.get_absolute_url())
        self.assertContains(resp, decklist2.archetype)
        self.assertContains(resp, decklist2.get_absolute_url())
        self.assertNotContains(resp, "Unmatched decklists")

    def test_shows_decklists_without_results(self):
        decklist = DecklistFactory(player=self.player, collection__event=self.event)
        decklist_without_result = DecklistFactory(collection__event=self.event)
        resp = self.client.get(reverse("event_details", args=[self.event.id]))
        self.assertContains(resp, decklist.archetype)
        self.assertContains(resp, decklist.get_absolute_url())
        self.assertContains(resp, decklist_without_result.archetype)
        self.assertContains(resp, decklist_without_result.get_absolute_url())
        self.assertContains(resp, f"by {decklist_without_result.player.name}")
        self.assertContains(resp, "Unmatched decklists")



