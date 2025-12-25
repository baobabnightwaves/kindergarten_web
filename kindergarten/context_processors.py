from .decorators import get_user_role

def user_role(request):
    """Контекстный процессор для определения роли пользователя"""
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
    """Контекстный процессор для навигации с учетом роли"""
    if not request.user.is_authenticated:
        return {'nav_sections': []}
    
    role = get_user_role(request.user)
    
    # Родитель - только свои дети и отчеты
    if role == 'parent':
        return {
            'nav_sections': [
                {
                    'name': 'Мои дети',
                    'items': [
                        {'name': 'Список моих детей', 'url': 'student_list'},
                    ]
                },
                {
                    'name': 'Отчеты',
                    'items': [
                        {'name': 'Мои отчеты', 'url': 'reports_dashboard'},
                    ]
                },
            ]
        }
    
    # Воспитатель - ученики своих групп, родители, посещаемость, отчеты
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
    
    # Директор и суперпользователь - доступ ко всему кроме управления пользователями (для директора)
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
        
        # Только суперпользователь имеет доступ к управлению пользователями
        if role == 'superuser':
            nav_sections.append({
                'name': 'Администрирование',
                'items': [
                    {'name': 'Пользователи', 'url': 'user_management'},
                ]
            })
        
        return {'nav_sections': nav_sections}
    
    return {'nav_sections': []}