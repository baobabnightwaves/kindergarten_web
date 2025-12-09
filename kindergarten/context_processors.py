
def navigation(request):
    """Контекстный процессор для навигации"""
    return {
        'nav_sections': [
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
                    {'name': 'События', 'url': 'event_list'},
                    {'name': 'Календарь', 'url': 'calendar'},
                ]
            },
            {
                'name': 'Отчеты',
                'items': [
                    {'name': 'Все отчеты', 'url': 'reports'},
                ]
            },
        ]
    }