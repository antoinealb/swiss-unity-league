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

import dataclasses
from collections.abc import Iterable
from typing import TypeAlias

from django.http import HttpResponseForbidden
from django.views.generic import DetailView
from django.views.generic.edit import UpdateView

from championship.models import Player
from decklists.forms import DecklistForm
from decklists.models import Collection, Decklist
from decklists.parser import DecklistParser
from oracle.models import Card


@dataclasses.dataclass
class DecklistEntry:
    qty: int
    name: str
    mana_cost: str | None = None
    mana_value: int | None = None
    type_line: str | None = None
    scryfall_uri: str | None = None


DecklistError: TypeAlias = str


def normalize_decklist(
    entries: Iterable[DecklistEntry],
) -> (list[DecklistEntry], list[DecklistError]):
    qty_by_cards = dict()
    for e in entries:
        try:
            qty_by_cards[e.name] += e.qty
        except KeyError:
            qty_by_cards[e.name] = e.qty

    return [DecklistEntry(v, k) for k, v in qty_by_cards.items()], []


def annotate_card_attributes(
    entries: Iterable[DecklistEntry],
) -> (list[DecklistEntry], list[DecklistError]):
    result = []
    errors = []
    for e in entries:
        try:
            card = Card.objects.get(name=e.name)
            e.mana_cost = card.mana_cost
            e.mana_value = card.mana_value
            e.scryfall_uri = card.scryfall_uri
        except Card.DoesNotExist:
            errors.append(f"Unknown card '{e.name}'")

        result.append(e)
    return result, errors


class DecklistView(DetailView):
    model = Decklist
    template_name = "decklists/decklist_details.html"
    object_name = "decklist"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # TODO: Error handling
        # TODO: Pipeline all the steps
        mainboard = DecklistParser.deck.parse(context["decklist"].mainboard).unwrap()
        mainboard = [tuple(line) for line in mainboard]
        mainboard = [DecklistEntry(qty, card) for (qty, card) in mainboard]
        mainboard, _ = normalize_decklist(mainboard)
        mainboard, errors = annotate_card_attributes(mainboard)

        context["mainboard"] = mainboard
        context["errors"] = errors

        sideboard = DecklistParser.deck.parse(context["decklist"].sideboard).unwrap()
        sideboard = [tuple(line) for line in sideboard]
        sideboard = [DecklistEntry(qty, card) for (qty, card) in sideboard]
        sideboard, _ = normalize_decklist(sideboard)
        sideboard, errors = annotate_card_attributes(sideboard)

        context["sideboard"] = sideboard
        context["errors"] += errors

        return context


class PlayerAutoCompleteMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = Player.objects.all()
        return context


class DecklistUpdateView(PlayerAutoCompleteMixin, UpdateView):
    model = Decklist
    form_class = DecklistForm
    template_name = "decklists/decklist_edit.html"

    def dispatch(self, request, *args, **kwargs):
        self.event = self.get_object()
        if not self.event.can_be_edited():
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)


class CollectionView(DetailView):
    model = Collection
    template_name = "decklists/collection_details.html"

    def get_decklists(self):
        return self.get_object().decklist_set.order_by("player__name", "-last_modified")

    def get_show_links(self):
        if self.get_object().event.organizer.user == self.request.user:
            return True

        if self.request.user.has_perm("decklists.view_decklist"):
            return True

        return self.get_object().decklists_published

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["decklists"] = self.get_decklists()
        context["show_links"] = self.get_show_links()
        return context
