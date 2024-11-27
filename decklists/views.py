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
import secrets
from collections import defaultdict
from collections.abc import Iterable
from typing import TypeAlias

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView

from championship.models import Event, Player
from championship.views.base import CustomDeleteView
from decklists.forms import CollectionForm, DecklistForm
from decklists.models import Collection, Decklist
from decklists.parser import DecklistParser
from oracle.models import Card, get_card_by_name

ORDERED_CARD_TYPES = [
    "Creature",
    "Planeswalker",
    "Battle",
    "Instant",
    "Sorcery",
    "Artifact",
    "Enchantment",
    "Land",
]


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


def parse_decklist(entries) -> FilterOutput:
    entries = [DecklistEntry(e.qty, e.name) for e in entries]
    return entries, []


def sort_decklist_by_mana_value(entries: Iterable[DecklistEntry]) -> FilterOutput:
    key = lambda c: (c.mana_value is None, c.mana_value, c.name)
    return sorted(entries, key=key), []


def pipe_filters(filters, entries) -> FilterOutput:
    result = entries
    errors = []

    for f in filters:
        result, err = f(result)
        errors += err

    return result, errors


def parse_section(section_text) -> FilterOutput:

    all_filters = [
        parse_decklist,
        normalize_decklist,
        annotate_card_attributes,
        sort_decklist_by_mana_value,
    ]

    return pipe_filters(all_filters, section_text)


def get_decklist_table_context(decklist: Decklist, split_decklist_by_type: bool = True):
    """
    Returns a context object used to render a decklist table. It containts:

    - decklist: The decklist object

    - cards_by_section: A dictionary with each section of the decklist. The key is the title of the section
    including total cards in the section and the value being the DecklistEntries in the given section.

    - errors: A list of errors found while parsing the decklist.

    - total_cards: The total number of cards in the decklist.
    """
    context = {"decklist": decklist}
    parsed = DecklistParser.deck.parse(decklist.content).unwrap()
    mainboard, errors_main = parse_section(parsed.mainboard)
    sideboard, errors_side = parse_section(parsed.sideboard)

    cards_by_section = {}
    if split_decklist_by_type:
        unknown_cards = []
        cards_by_type = defaultdict(list)
        for card in mainboard:
            main_card_type = next(
                (
                    type
                    for type in ORDERED_CARD_TYPES
                    if card.type_line and type in card.type_line
                ),
                None,
            )
            if main_card_type is None:
                unknown_cards.append(card)
            else:
                cards_by_type[main_card_type].append(card)
        cards_by_section = {
            f"{card_type}s": cards_by_type[card_type]
            for card_type in ORDERED_CARD_TYPES
            if card_type in cards_by_type
        }
        if unknown_cards:
            cards_by_section["Unknown"] = unknown_cards
    else:
        cards_by_section["Mainboard"] = mainboard

    cards_by_section["Sideboard"] = sideboard

    cards_by_section = {
        f"{section} ({sum(c.qty for c in cards_by_section[section])})": cards_by_section[
            section
        ]
        for section in cards_by_section
    }

    context["cards_by_section"] = cards_by_section  # type: ignore
    context["errors"] = errors_main + errors_side  # type: ignore
    context["total_cards"] = sum(c.qty for cards in cards_by_section.values() for c in cards)  # type: ignore
    return context


class DecklistView(DetailView):
    model = Decklist
    template_name = "decklists/decklist_details.html"
    object_name = "decklist"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        decklist = context["decklist"]
        # By default, we sort by type, but we can also sort by manavalue for
        # deckchecks.
        sort_by_type = True
        if self.request.GET.get("sort") == "manavalue":
            sort_by_type = False

        context.update(
            get_decklist_table_context(decklist, split_decklist_by_type=sort_by_type)
        )
        if (
            decklist.can_be_edited()
            or decklist.collection.event.organizer.user == self.request.user
            or "staff_key" in self.request.GET
        ):
            staff_query_param = (
                f"?staff_key={self.request.GET['staff_key']}"
                if "staff_key" in self.request.GET
                else ""
            )
            context["edit_decklist_url"] = (
                reverse("decklist-update", args=[decklist.id]) + staff_query_param
            )
            context["delete_decklist_url"] = (
                reverse("decklist-delete", args=[decklist.id]) + staff_query_param
            )
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
        if not (
            decklist.can_be_edited()
            or decklist.collection.event.organizer.user == request.user
            or decklist.collection.staff_key == request.GET.get("staff_key")
        ):
            messages.error(
                request,
                "This decklist cannot be edited because you are past the submission deadline.",
            )
            return redirect(reverse("decklist-details", args=[decklist.id]))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self) -> str:
        return super().get_success_url() + (
            f"?staff_key={self.request.GET['staff_key']}"
            if "staff_key" in self.request.GET
            else ""
        )


class DecklistCreateView(SuccessMessageMixin, CreateView):
    model = Decklist
    form_class = DecklistForm
    template_name = "decklists/decklist_edit.html"
    success_message = "Decklist was saved succesfully."

    def get_collection(self) -> Collection:
        collection_pk = self.request.GET["collection"]
        return Collection.objects.get(pk=collection_pk)

    def dispatch(self, request, *args, **kwargs):
        collection = self.get_collection()
        if (
            collection.is_past_deadline
            and not collection.event.organizer.user == request.user
        ):
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


class DecklistDeleteView(CustomDeleteView):
    model = Decklist

    def get_success_url(self):
        return reverse("collection-details", args=[self.object.collection.id])

    def allowed_to_delete(self, object, request):
        return (
            object.can_be_edited()
            or object.collection.event.organizer.user == request.user
            or secrets.compare_digest(
                object.collection.staff_key, request.GET.get("staff_key", "")
            )
        )


class CollectionView(DetailView):
    model = Collection
    template_name = "decklists/collection_details.html"

    def get_decklists(self):
        return self.object.decklist_set.select_related("player", "collection").order_by(
            "player__name", "-last_modified"
        )

    def get_staff_link(self):
        link = self.request.build_absolute_uri(
            self.object.get_absolute_url() + f"?staff_key={self.object.staff_key}"
        )
        if self.object.event.organizer.user == self.request.user:
            return link

        if self.request.user.has_perm("decklists.view_decklist"):
            return link

        return None

    def get_using_staff_link(self):
        # If decklist are not published, only show them to a user presenting
        # the right sharing key. Use constant-time comparison.
        k1 = self.object.staff_key
        k2 = self.request.GET.get("staff_key", "")
        return secrets.compare_digest(k1, k2)

    def get_show_decklist_links(self):
        if self.object.decklists_published:
            return True

        return self.get_using_staff_link()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["decklists"] = self.get_decklists()
        context["staff_link"] = self.get_staff_link()
        context["show_decklist_links"] = self.get_show_decklist_links()
        context["using_staff_link"] = self.get_using_staff_link()
        context["owned_decklists"] = self.request.session.get("owned_decklists", [])
        # Show owned decklists first
        context["decklists"] = sorted(
            context["decklists"],
            key=lambda d: d.id.hex in context["owned_decklists"],
            reverse=True,
        )
        return context


class CollectionCreateView(SuccessMessageMixin, CreateView):
    model = Collection
    form_class = CollectionForm
    template_name = "decklists/collection_edit.html"
    success_message = "Collection was saved succesfully."

    def dispatch(self, request, *args, **kwargs):
        event_pk = self.request.GET["event"]
        self.event = get_object_or_404(Event, pk=event_pk)
        if self.event.organizer.user != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.event
        return context

    def get_form_kwargs(self, *args, **kwargs):
        res = super().get_form_kwargs(*args, **kwargs)
        res["event"] = self.event
        return res


class CollectionUpdateView(SuccessMessageMixin, UpdateView):
    model = Collection
    form_class = CollectionForm
    template_name = "decklists/collection_edit.html"
    success_message = "Collection was saved succesfully."

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, collection__pk=self.kwargs.get("pk"))
        if self.event.organizer.user != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.event
        return context
