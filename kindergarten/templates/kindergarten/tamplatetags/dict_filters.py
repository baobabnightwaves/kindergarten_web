from django import template
register = template.Library()
@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    return dictionary.get(key)
@register.filter
def get_attendance(dictionary, student_id):
    if dictionary is None:
        return None
    return dictionary.get(student_id)