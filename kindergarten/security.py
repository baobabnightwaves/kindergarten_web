from django.core.exceptions import ValidationError
from django.core.validators import validate_integer
import re
def sanitize_integer(value, min_value=None, max_value=None):
    if value is None or value == '':
        return None
    try:
        int_value = int(value)
        if min_value is not None and int_value < min_value:
            raise ValidationError(f'Значение должно быть не меньше {min_value}')
        if max_value is not None and int_value > max_value:
            raise ValidationError(f'Значение должно быть не больше {max_value}')
        return int_value
    except (ValueError, TypeError):
        raise ValidationError('Недопустимое числовое значение')
def sanitize_date_string(date_string):
    if not date_string:
        return None
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, str(date_string)):
        raise ValidationError('Неверный формат даты. Ожидается YYYY-MM-DD')
    try:
        year, month, day = map(int, date_string.split('-'))
        if year < 1900 or year > 2100:
            raise ValidationError('Год должен быть в диапазоне 1900-2100')
        if month < 1 or month > 12:
            raise ValidationError('Месяц должен быть в диапазоне 1-12')
        if day < 1 or day > 31:
            raise ValidationError('День должен быть в диапазоне 1-31')
        return date_string
    except ValueError:
        raise ValidationError('Неверный формат даты')
def sanitize_search_query(query, max_length=100):
    if not query:
        return ''
    query = str(query)[:max_length]
    dangerous_patterns = [
        '--', ';', '/*', '*/', 'xp_', 'sp_', 
        'drop', 'delete', 'insert', 'update', 'select',
        'union', 'exec', 'execute', 'script',
        "'or'", '"or"', "1=1", "1' or '1", "' or '"
    ]
    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if pattern in query_lower:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'Потенциальная SQL-инъекция заблокирована: {query}')
            raise ValidationError('Недопустимые символы в поисковом запросе')
    return query.strip()
def sanitize_choice_field(value, valid_choices):
    if not value:
        return ''
    if valid_choices and isinstance(valid_choices[0], (list, tuple)):
        valid_values = [str(choice[0]) for choice in valid_choices]
    else:
        valid_values = [str(choice) for choice in valid_choices]
    if str(value) not in valid_values:
        raise ValidationError(f'Недопустимое значение: {value}')
    return str(value)
def validate_file_upload(uploaded_file, allowed_extensions=None, max_size_mb=5):
    if not uploaded_file:
        return
    max_size = max_size_mb * 1024 * 1024
    if uploaded_file.size > max_size:
        raise ValidationError(f'Размер файла не должен превышать {max_size_mb} МБ')
    if allowed_extensions:
        import os
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(
                f'Недопустимое расширение файла. Разрешены: {", ".join(allowed_extensions)}'
            )
def sanitize_phone_number(phone):
    if not phone:
        return ''
    phone = re.sub(r'[^\d+\-() ]', '', str(phone))
    digits_only = re.sub(r'[^\d]', '', phone)
    if len(digits_only) < 10 or len(digits_only) > 15:
        raise ValidationError('Неверный формат номера телефона')
    return phone.strip()
def sanitize_text_field(text, max_length=1000, allow_html=False):
    if not text:
        return ''
    text = str(text)[:max_length]
    if not allow_html:
        text = re.sub(r'<[^>]+>', '', text)
    return text.strip()
def validate_pagination_params(page_number, per_page=20, max_per_page=100):
    try:
        page = sanitize_integer(page_number, min_value=1)
        if page is None:
            page = 1
    except ValidationError:
        page = 1
    try:
        per_page_val = sanitize_integer(per_page, min_value=1, max_value=max_per_page)
        if per_page_val is None:
            per_page_val = 20
    except ValidationError:
        per_page_val = 20
    return page, per_page_val
SAFE_HTTP_METHODS = ['GET', 'HEAD', 'OPTIONS']
DANGEROUS_SQL_KEYWORDS = [
    'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE',
    'EXEC', 'EXECUTE', 'SCRIPT', 'UNION', 'SELECT', '--', '/*', '*/',
    'xp_', 'sp_', 'INFORMATION_SCHEMA', 'SYSOBJECTS', 'SYSCOLUMNS'
]
