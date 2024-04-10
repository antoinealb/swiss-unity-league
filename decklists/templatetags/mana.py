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

import logging

from django import template
from django.utils.safestring import mark_safe

from parsita import Success

from decklists.parser import (
    AlternativeMana,
    Color,
    Colorless,
    Hybrid,
    ManaParser,
    Phyrexian,
    Snow,
)

register = template.Library()


@register.filter("mana", is_safe=True, needs_autoescape=False)
def mana(mana_spec):
    if not mana_spec:
        return ""
    if isinstance(mana_spec, str):
        parsed = ManaParser.mana.parse(mana_spec)
        if isinstance(parsed, Success):
            mana_spec = parsed.unwrap()
        else:
            logging.warning("Could not parse mana %s", mana_spec)
            return mana_spec

    if isinstance(mana_spec, AlternativeMana):
        return mark_safe(" // ".join(mana(s) for s in mana_spec.content))

    def _class_suffix(spec):
        if isinstance(spec, int):
            return str(spec)
        elif isinstance(spec, str):
            return spec.lower()
        elif isinstance(spec, Color):
            return spec.value.lower()
        elif isinstance(spec, Phyrexian):
            return _class_suffix(spec.color) + "p"
        elif isinstance(spec, Hybrid):
            return "".join(_class_suffix(s) for s in spec.colors)
        elif spec == Snow:
            return "s"
        elif spec == Colorless:
            return "c"

    result = []
    for spec in mana_spec:
        inner = _class_suffix(spec)
        result.append(f'<i class="ms ms-cost ms-{inner}"></i>')

    return mark_safe("".join(result))
