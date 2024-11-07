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

from articles.parser import CardTag, DecklistTag, ImageTag, extract_tags
from decklists.models import Decklist
from decklists.views import get_decklist_table_context
from oracle.models import Card, get_card_by_name

register = template.Library()


@register.filter("article_tags", needs_autoescape=False, is_safe=True)
def process_article_args(text: str):
    result = []
    card_template = get_template("decklists/card_modal_instance.html")
    decklist_section_template = get_template("articles/decklist_card.html")

    for chunk in extract_tags(text):
        if isinstance(chunk, str):
            result.append(chunk)
        elif isinstance(chunk, CardTag):
            try:
                card = get_card_by_name(chunk.card_name)
                rendered = card_template.render(context={"card": card})
                result.append(mark_safe(rendered))
            except Card.DoesNotExist:
                result.append(f"[[{chunk.card_name}]]")
        elif isinstance(chunk, DecklistTag):
            try:
                decklist = Decklist.objects.select_related(
                    "player", "collection__event"
                ).get(id=chunk.uid)
                context = get_decklist_table_context(decklist)
                result.append(decklist_section_template.render(context=context))
            except Decklist.DoesNotExist:
                result.append(f"Unknown decklist {chunk.uid}")
        elif isinstance(chunk, ImageTag):
            result.append(
                f'<img class="img-fluid" src="{chunk.url}" alt="{chunk.alt_text}" />'
            )

    return "".join(result)
