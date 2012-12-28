from django.template import Library

register = Library()

@register.filter
def as_range(value):
    """
      Filter - returns a list containing range made from given value
      Usage (in template):

      {% for i in 3|get_range %}
        {{ i }}
      {% endfor %}
    """
    return range(value)
