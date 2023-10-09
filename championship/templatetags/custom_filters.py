from django import template

register = template.Library()


@register.filter(name="range")
def rangeFilter(value):
    return range(value)
