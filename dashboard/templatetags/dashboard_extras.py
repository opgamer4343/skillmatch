from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key)
    return None


@register.filter
def get_item(dictionary, key):
    """Get dict item by key in template: {{ mydict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(int(key) if str(key).isdigit() else key, 0)
    return 0