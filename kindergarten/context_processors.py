from .decorators import get_user_role
def user_role(request):
    if not request.user.is_authenticated:
        return {
            'user_role': None,
            'is_parent': False,
            'is_teacher': False,
            'is_director': False,
            'is_superuser': False,
        }
    role = get_user_role(request.user)
    return {
        'user_role': role,
        'is_parent': role == 'parent',
        'is_teacher': role == 'teacher',
        'is_director': role == 'director',
        'is_superuser': role == 'superuser',
    }
def navigation(request):
    if not request.user.is_authenticated:
        return {'nav_sections': []}
    role = get_user_role(request.user)
    if role == 'parent':
        return {
            'nav_sections': [
                {
                    'name': 'Мои дети',
                    'items': [
                        {'name': 'Мои дети', 'url': 'student_list'},
                    ]
                },
                {
                    'name': 'Отчеты',
                    'items': [
                        {'name': 'Отчеты', 'url': 'parent_reports'},
                    ]
                },
            ]
        }
    elif role == 'teacher':
        return {
            'nav_sections': [
                {
                    'name': 'Управление',
                    'items': [
                        {'name': 'Ученики', 'url': 'student_list'},
                        {'name': 'Родители', 'url': 'parent_list'},
                        {'name': 'Мои группы', 'url': 'group_list'},
                    ]
                },
                {
                    'name': 'Учет',
                    'items': [
                        {'name': 'Посещаемость', 'url': 'attendance_list'},
                    ]
                },
                {
                    'name': 'Отчеты',
                    'items': [
                        {'name': 'Отчеты', 'url': 'reports_dashboard'},
                    ]
                },
            ]
        }
    elif role in ['director', 'superuser']:
        nav_sections = [
            {
                'name': 'Управление',
                'items': [
                    {'name': 'Ученики', 'url': 'student_list'},
                    {'name': 'Воспитатели', 'url': 'teacher_list'},
                    {'name': 'Группы', 'url': 'group_list'},
                    {'name': 'Родители', 'url': 'parent_list'},
                ]
            },
            {
                'name': 'Учет',
                'items': [
                    {'name': 'Посещаемость', 'url': 'attendance_list'},
                ]
            },
            {
                'name': 'Отчеты',
                'items': [
                    {'name': 'Отчеты', 'url': 'reports_dashboard'},
                ]
            },
        ]
        if role == 'superuser':
            nav_sections.append({
                'name': 'Администрирование',
                'items': [
                    {'name': 'Пользователи', 'url': 'user_management'},
                ]
            })
        return {'nav_sections': nav_sections}
    return {'nav_sections': []}