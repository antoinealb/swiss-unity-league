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

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView

from championship.models import Player
from decklists.forms import DecklistForm
from decklists.models import Collection, Decklist
from decklists.parser import DecklistParser
from oracle.models import Card, get_card_by_name


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
            card = get_card_by_name(e.name)
            e.name = card.name
            e.mana_cost = card.mana_cost
            e.mana_value = card.mana_value
            e.scryfall_uri = card.scryfall_uri
        except Card.DoesNotExist:
            errors.append(f"Unknown card '{e.name}'")

        result.append(e)
    return result, errors


def parse_decklist(content: str) -> (list[DecklistEntry], list[DecklistError]):
    entries = DecklistParser.deck.parse(content).unwrap()
    entries = [tuple(line) for line in entries]
    entries = [DecklistEntry(qty, card) for (qty, card) in entries]
    return entries, []


def sort_decklist(
    entries: Iterable[DecklistEntry],
) -> (list[DecklistEntry], list[DecklistError]):
    key = lambda c: (c.mana_value is None, c.mana_value, c.name)
    return sorted(entries, key=key), []


def pipe_filters(filters, entries) -> (list[DecklistEntry], list[DecklistError]):
    result = entries
    errors = []

    for f in filters:
        result, err = f(result)
        errors += err

    return result, errors


class DecklistView(DetailView):
    model = Decklist
    template_name = "decklists/decklist_details.html"
    object_name = "decklist"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        all_filters = [
            parse_decklist,
            normalize_decklist,
            annotate_card_attributes,
            sort_decklist,
        ]

        mainboard, errors_main = pipe_filters(
            all_filters, context["decklist"].mainboard
        )
        sideboard, errors_side = pipe_filters(
            all_filters, context["decklist"].sideboard
        )

        context["mainboard"] = mainboard
        context["sideboard"] = sideboard

        context["errors"] = errors_main + errors_side

        context["mainboard_total"] = sum(c.qty for c in mainboard)
        context["sideboard_total"] = sum(c.qty for c in sideboard)

        return context


class PlayerAutoCompleteMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["players"] = Player.objects.all()
        return context


class DecklistUpdateView(PlayerAutoCompleteMixin, SuccessMessageMixin, UpdateView):
    model = Decklist
    form_class = DecklistForm
    template_name = "decklists/decklist_edit.html"
    success_message = "Decklist was saved succesfully."

    def dispatch(self, request, *args, **kwargs):
        decklist = self.get_object()
        if not decklist.can_be_edited():
            messages.error(
                request,
                "This decklist cannot be edited because you are past the submission deadline.",
            )
            return redirect(reverse("decklist-details", args=[decklist.id]))
        return super().dispatch(request, *args, **kwargs)


class DecklistCreateView(SuccessMessageMixin, CreateView):
    model = Decklist
    form_class = DecklistForm
    template_name = "decklists/decklist_edit.html"
    success_message = "Decklist was saved succesfully."

    def get_collection(self) -> Collection:
        collection_pk = self.request.GET["collection"]
        return Collection.objects.get(pk=collection_pk)

    def dispatch(self, request, *args, **kwargs):
        if self.get_collection().is_past_deadline():
            messages.error(
                request,
                "This decklist cannot be created because you are past the submission deadline.",
            )

            return redirect(
                reverse("collection-details", args=[self.get_collection().id])
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self, *args, **kwargs):
        res = super().get_form_kwargs(*args, **kwargs)
        res["collection"] = self.get_collection()

        return res

    def form_valid(self, form):
        resp = super().form_valid(form)
        try:
            self.request.session["owned_decklists"] += [self.object.id.hex]
        except KeyError:
            self.request.session["owned_decklists"] = [self.object.id.hex]
        return resp


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
        context["owned_decklists"] = self.request.session.get("owned_decklists", [])
        return context
