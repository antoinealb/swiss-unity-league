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

import datetime
import re

from django import template
from django.utils import formats

register = template.Library()


@register.filter(name="range")
def rangeFilter(value):
    return range(value)


@register.simple_tag
def verbose_name(model):
    return model._meta.verbose_name


@register.filter
def weekday_date(value):
    if isinstance(value, datetime.date):
        format_str = "D, d.m.Y"
        return formats.date_format(value, format_str)
    return value


@register.filter(name="initials")
def initials(name):
    """Returns a name with only their initials, aside from first name.

    >>> initials("Bob Johnson")
    'Bob J.'
    """
    components = re.split(r"[\s-]", name)
    components = [c for c in components if c]
    # We keep the first name complete and initial the rest
    for c in components[1:]:
        name = name.replace(c, f"{c[0]}.")
    return name


@register.filter(name="percentage")
def percentage(value):
    """Returns the float value formatted as a percentage, with a single digit.

    >>> percentage(0.1)
    '10.0%'
    """
    return "{:.1%}".format(value)
