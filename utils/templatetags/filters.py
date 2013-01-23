from django.template import Library

register = Library()

@register.filter
def as_range(value):
    """
      Filter - returns a list containing range made from given value
      Usage (in template):

      {% for i in 3|as_range %}
        {{ i }}
      {% endfor %}
    """
    if value:
        return range(value)
    else:
        return []
