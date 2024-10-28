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

from django import template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from articles.parser import CardTag, DecklistTag, extract_tags
from decklists.models import Decklist
from decklists.views import parse_section
from oracle.models import get_card_by_name

register = template.Library()


@register.filter("article_tags", needs_autoescape=False, is_safe=True)
def process_article_args(text: str):
    result = []
    card_template = get_template("decklists/card_modal_instance.html")
    decklist_section_template = get_template("articles/decklist.html")

    for chunk in extract_tags(text):
        if isinstance(chunk, str):
            result.append(chunk)
        elif isinstance(chunk, CardTag):
            card = get_card_by_name(chunk.card_name)
            rendered = card_template.render(context={"card": card})
            result.append(mark_safe(rendered))
        elif isinstance(chunk, DecklistTag):
            try:
                decklist = Decklist.objects.get(id=chunk.uid)
                mainboard, errors_mb = parse_section(decklist.mainboard)
                sideboard, errors_sb = parse_section(decklist.sideboard)
                errors = errors_mb + errors_sb
                player = decklist.player
                archetype = decklist.archetype
            except Decklist.DoesNotExist:
                errors = [f"Unknown decklist {chunk.uid}"]
                mainboard = []
                sideboard = []
                player = None
                archetype = None
            rendered = decklist_section_template.render(
                context={
                    "mainboard": mainboard,
                    "sideboard": sideboard,
                    "errors": errors,
                    "player": player,
                    "archetype": archetype,
                }
            )
            result.append(rendered)

    return "".join(result)
