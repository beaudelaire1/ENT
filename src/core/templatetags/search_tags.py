from django import template

from core.search import highlight_excerpt

register = template.Library()


@register.filter
def highlight(text, query):
    """`{{ entry.body|highlight:query }}` : voir `core.search.highlight_excerpt`."""
    return highlight_excerpt(text, query)
