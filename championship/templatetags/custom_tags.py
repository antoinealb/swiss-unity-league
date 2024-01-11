from django import template
from django.urls import reverse

register = template.Library()


@register.filter(name="range")
def rangeFilter(value):
    return range(value)


@register.simple_tag
def verbose_name(model):
    return model._meta.verbose_name


@register.simple_tag
def season_url(view_name, slug, pk=None):
    """Needed to allow the season dropdown to have an optional url argument called pk."""
    if pk:
        return reverse(view_name, kwargs={"slug": slug, "pk": pk})
    else:
        return reverse(view_name, kwargs={"slug": slug})
