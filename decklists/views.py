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
    image_uri: str | None = None


DecklistError: TypeAlias = str
FilterOutput: TypeAlias = tuple[list[DecklistEntry], list[DecklistError]]


def normalize_decklist(entries: Iterable[DecklistEntry]) -> FilterOutput:
    qty_by_cards: dict[str, int] = {}
    for e in entries:
        try:
            qty_by_cards[e.name] += e.qty
        except KeyError:
            qty_by_cards[e.name] = e.qty

    return [DecklistEntry(v, k) for k, v in qty_by_cards.items()], []


def annotate_card_attributes(entries: Iterable[DecklistEntry]) -> FilterOutput:
    result = []
    errors = []
    for e in entries:
        try:
            card = get_card_by_name(e.name)
            e.name = card.name
            e.mana_cost = card.mana_cost
            e.mana_value = card.mana_value
            e.type_line = card.type_line
            e.scryfall_uri = card.scryfall_uri
            e.image_uri = card.image_uri
        except Card.DoesNotExist:
            errors.append(f"Unknown card '{e.name}'")

        result.append(e)
    return result, errors


def parse_decklist(content: str) -> FilterOutput:
    entries = DecklistParser.deck.parse(content).unwrap()
    entries = [tuple(line) for line in entries]
    entries = [DecklistEntry(qty, card) for (qty, card) in entries]
    return entries, []


def sort_decklist_by_mana_value(entries: Iterable[DecklistEntry]) -> FilterOutput:
    key = lambda c: (c.mana_value is None, c.mana_value, c.name)
    return sorted(entries, key=key), []


def sort_decklist_by_type(entries: Iterable[DecklistEntry]) -> FilterOutput:
    categories = [
        ["Creature"],
        ["Battle"],
        ["Planeswalker"],
        ["Instant", "Sorcery"],
        ["Artifact"],
        ["Enchantment"],
        ["Land"],
    ]

    def find_category(type_line):
        end = len(categories)
        if type_line is None:
            return end

        for i, types in enumerate(categories):
            if any(t in type_line for t in types):
                return i
        # We send every unknown type at the end
        return end

    key = lambda c: (
        find_category(c.type_line),
        c.mana_value is None,
        c.mana_value,
        c.name,
    )

    return sorted(entries, key=key), []


def pipe_filters(filters, entries) -> FilterOutput:
    result = entries
    errors = []

    for f in filters:
        result, err = f(result)
        errors += err

    return result, errors


def parse_section(section_text: str, sort_by_type: bool = True) -> FilterOutput:
    if sort_by_type:
        sort_fn = sort_decklist_by_type
    else:
        sort_fn = sort_decklist_by_mana_value

    all_filters = [
        parse_decklist,
        normalize_decklist,
        annotate_card_attributes,
        sort_fn,
    ]

    return pipe_filters(all_filters, section_text)


class DecklistView(DetailView):
    model = Decklist
    template_name = "decklists/decklist_details.html"
    object_name = "decklist"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # For players we show the list by types, but for TOs / Judges, only
        # sorted by mana value for deck checks.
        sort_decklist_by_type = self.request.user.is_anonymous

        mainboard, errors_main = parse_section(
            context["decklist"].mainboard, sort_by_type=sort_decklist_by_type
        )
        sideboard, errors_side = parse_section(
            context["decklist"].sideboard, sort_by_type=sort_decklist_by_type
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
