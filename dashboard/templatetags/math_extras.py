from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtract the arg from the value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0
        
@register.filter
def multiply(value, arg):
    """Multiply the value by the arg."""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0
        
@register.filter
def divide(value, arg):
    """Divide the value by the arg."""
    try:
        return int(value) / int(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0