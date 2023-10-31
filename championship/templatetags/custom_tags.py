from django import template

register = template.Library()


@register.filter(name="range")
def rangeFilter(value):
    return range(value)


@register.simple_tag
def verbose_name(model):
    return model._meta.verbose_name
