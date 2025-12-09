from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получает значение из словаря по ключу"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def get_attendance(dictionary, student_id):
    """Специальный фильтр для получения записи посещаемости"""
    if dictionary is None:
        return None
    return dictionary.get(student_id)