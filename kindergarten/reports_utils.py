# kindergarten/reports_utils.py
import threading
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for charts
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import date, timedelta
from django.db.models import Count, Sum, Avg, Q, F
from django.db import connection
from collections import defaultdict
import json

def get_report_data_threaded(user, report_type, filters=None):
    """Запуск формирования отчета в отдельном потоке"""
    if filters is None:
        filters = {}
    
    # Создаем поток для генерации отчета
    thread = threading.Thread(
        target=generate_report_data,
        args=(user, report_type, filters)
    )
    thread.daemon = True
    thread.start()
    
    return thread

def generate_report_data(user, report_type, filters):
    """Генерация данных для отчета"""
    from .models import Student, Teacher, Group, Parent, Attendance, StudentParent
    
    try:
        # Определяем, какие данные доступны пользователю
        if user.groups.filter(name='Родители').exists():
            # Для родителя - только данные о его ребенке
            if hasattr(user, 'parent_profile'):
                parent = user.parent_profile
                child_ids = parent.studentparent_set.values_list('student_id', flat=True)
                return get_parent_report_data(parent, child_ids, report_type, filters)
        
        elif user.groups.filter(name='Воспитатели').exists():
            # Для воспитателя - только его группы
            if hasattr(user, 'teacher_profile'):
                teacher = user.teacher_profile
                teacher_groups = Group.objects.filter(teacher=teacher)
                return get_teacher_report_data(teacher, teacher_groups, report_type, filters)
        
        elif user.groups.filter(name='Заведующие').exists() or user.is_superuser:
            # Для администраторов и суперпользователей - все данные
            return get_admin_report_data(user, report_type, filters)
    
    except Exception as e:
        print(f"Ошибка при генерации отчета: {e}")
        return None

def get_parent_report_data(parent, child_ids, report_type, filters):
    """Данные отчета для родителя"""
    from .models import Student, Attendance, Group
    
    children = Student.objects.filter(pk__in=child_ids)
    
    if report_type == 'attendance_by_month':
        # Посещаемость по месяцам
        data = []
        for child in children:
            attendance_by_month = Attendance.objects.filter(
                student=child,
                attendance_date__year=date.today().year
            ).extra({
                'month': "strftime('%%m', attendance_date)"
            }).values('month').annotate(
                present=Count('pk', filter=Q(status=True)),
                absent=Count('pk', filter=Q(status=False))
            ).order_by('month')
            
            for item in attendance_by_month:
                data.append({
                    'child': child.student_fio,
                    'month': item['month'],
                    'present': item['present'],
                    'absent': item['absent']
                })
        
        return {
            'type': 'table',
            'title': f'Посещаемость детей за {date.today().year} год',
            'data': data
        }
    
    elif report_type == 'child_info':
        # Информация о ребенке
        child_info = []
        for child in children:
            child_info.append({
                'ФИО': child.student_fio,
                'Дата рождения': child.student_birthday,
                'Возраст': child.age(),
                'Группа': child.group.group_name if child.group else 'Не назначена',
                'Дата поступления': child.student_date_in,
                'Статус': 'Активен' if child.is_active() else 'Выпущен'
            })
        
        return {
            'type': 'table',
            'title': 'Информация о детях',
            'data': child_info
        }

def get_teacher_report_data(teacher, teacher_groups, report_type, filters):
    """Данные отчета для воспитателя"""
    from .models import Student, Attendance, Group
    
    group_ids = teacher_groups.values_list('pk', flat=True)
    students = Student.objects.filter(group_id__in=group_ids)
    
    if report_type == 'group_attendance':
        # Посещаемость по группам
        attendance_data = []
        for group in teacher_groups:
            students_in_group = students.filter(group=group)
            for student in students_in_group:
                attendance_stats = Attendance.objects.filter(
                    student=student,
                    attendance_date__gte=date.today() - timedelta(days=30)
                ).aggregate(
                    present=Count('pk', filter=Q(status=True)),
                    absent=Count('pk', filter=Q(status=False))
                )
                
                attendance_data.append({
                    'group': group.group_name,
                    'student': student.student_fio,
                    'present': attendance_stats['present'] or 0,
                    'absent': attendance_stats['absent'] or 0,
                    'attendance_rate': round(
                        (attendance_stats['present'] or 0) / 
                        ((attendance_stats['present'] or 0) + (attendance_stats['absent'] or 0)) * 100, 1
                    ) if ((attendance_stats['present'] or 0) + (attendance_stats['absent'] or 0)) > 0 else 0
                })
        
        return {
            'type': 'table',
            'title': f'Посещаемость по группам ({teacher.teacher_fio})',
            'data': attendance_data
        }
    
    elif report_type == 'monthly_stats':
        # Статистика по месяцам
        monthly_data = []
        for month in range(1, 13):
            attendance_stats = Attendance.objects.filter(
                student__group__in=teacher_groups,
                attendance_date__year=date.today().year,
                attendance_date__month=month
            ).aggregate(
                present=Count('pk', filter=Q(status=True)),
                absent=Count('pk', filter=Q(status=False)),
                total=Count('pk')
            )
            
            if attendance_stats['total'] > 0:
                monthly_data.append({
                    'month': month,
                    'present': attendance_stats['present'] or 0,
                    'absent': attendance_stats['absent'] or 0,
                    'attendance_rate': round(
                        (attendance_stats['present'] or 0) / attendance_stats['total'] * 100, 1
                    )
                })
        
        return {
            'type': 'chart_data',
            'title': f'Статистика посещаемости по месяцам',
            'data': monthly_data
        }

def get_admin_report_data(user, report_type, filters):
    """Данные отчета для администратора и суперпользователя"""
    from .models import Student, Teacher, Group, Parent, Attendance
    
    if report_type == 'overall_stats':
        # Общая статистика
        today = date.today()
        
        # Статистика по группам
        group_stats = []
        for group in Group.objects.all():
            students_count = group.current_students_count()
            attendance_today = Attendance.objects.filter(
                student__group=group,
                attendance_date=today
            ).aggregate(
                present=Count('pk', filter=Q(status=True)),
                absent=Count('pk', filter=Q(status=False))
            )
            
            group_stats.append({
                'group_name': group.group_name,
                'category': group.get_group_category_display(),
                'teacher': group.teacher.teacher_fio if group.teacher else 'Не назначен',
                'students_count': students_count,
                'capacity': group.max_capacity,
                'fill_percentage': round(students_count / group.max_capacity * 100, 1) if group.max_capacity > 0 else 0,
                'present_today': attendance_today['present'] or 0,
                'absent_today': attendance_today['absent'] or 0,
                'attendance_rate': round(
                    (attendance_today['present'] or 0) / 
                    ((attendance_today['present'] or 0) + (attendance_today['absent'] or 0)) * 100, 1
                ) if ((attendance_today['present'] or 0) + (attendance_today['absent'] or 0)) > 0 else 0
            })
        
        # Возрастная статистика
        age_stats = Student.objects.filter(
            student_date_out__isnull=True
        ).extra({
            'age': "date('now') - student_birthday"
        }).values('age').annotate(
            count=Count('pk')
        ).order_by('age')
        
        # Статистика по воспитателям
        teacher_stats = []
        for teacher in Teacher.objects.all():
            groups = Group.objects.filter(teacher=teacher)
            students_count = Student.objects.filter(group__in=groups).count()
            
            teacher_stats.append({
                'teacher_name': teacher.teacher_fio,
                'position': teacher.teacher_position,
                'groups_count': groups.count(),
                'students_count': students_count
            })
        
        return {
            'type': 'dashboard_data',
            'group_stats': group_stats,
            'age_stats': list(age_stats),
            'teacher_stats': teacher_stats,
            'total_students': Student.objects.filter(student_date_out__isnull=True).count(),
            'total_teachers': Teacher.objects.count(),
            'total_groups': Group.objects.count(),
            'total_parents': Parent.objects.count(),
            'attendance_today': Attendance.objects.filter(attendance_date=today, status=True).count(),
            'absent_today': Attendance.objects.filter(attendance_date=today, status=False).count(),
        }
    
    elif report_type == 'detailed_attendance':
        # Детальная посещаемость с фильтрами
        query = Attendance.objects.all()
        
        if filters.get('start_date'):
            query = query.filter(attendance_date__gte=filters['start_date'])
        if filters.get('end_date'):
            query = query.filter(attendance_date__lte=filters['end_date'])
        if filters.get('group_id'):
            query = query.filter(student__group_id=filters['group_id'])
        if filters.get('teacher_id'):
            query = query.filter(student__group__teacher_id=filters['teacher_id'])
        
        attendance_data = query.select_related(
            'student', 'student__group', 'noted_by'
        ).values(
            'attendance_date',
            'student__student_fio',
            'student__group__group_name',
            'status',
            'reason',
            'noted_by__teacher_fio'
        ).order_by('-attendance_date')[:100]  # Ограничиваем 100 записей
        
        return {
            'type': 'table',
            'title': 'Детальная посещаемость',
            'data': list(attendance_data)
        }
    
    elif report_type == 'financial_report':
        # Финансовый отчет (предполагаем, что есть поле оплаты)
        # Создаем тестовые данные
        financial_data = []
        for group in Group.objects.all():
            students_count = group.current_students_count()
            # Предполагаем стоимость 10000 руб. в месяц на ребенка
            monthly_revenue = students_count * 10000
            
            financial_data.append({
                'group': group.group_name,
                'students_count': students_count,
                'monthly_revenue': monthly_revenue,
                'yearly_revenue': monthly_revenue * 12,
                'teacher_salary': 50000 if group.teacher else 0,  # Предполагаемая зарплата
                'net_profit': monthly_revenue - (50000 if group.teacher else 0)
            })
        
        return {
            'type': 'table',
            'title': 'Финансовый отчет по группам',
            'data': financial_data
        }

def create_chart(chart_type, data, title):
    """Создание диаграммы"""
    plt.figure(figsize=(10, 6))
    
    if chart_type == 'bar':
        labels = [item['label'] for item in data]
        values = [item['value'] for item in data]
        plt.bar(labels, values)
        plt.title(title)
        plt.xticks(rotation=45)
    
    elif chart_type == 'pie':
        labels = [item['label'] for item in data]
        values = [item['value'] for item in data]
        plt.pie(values, labels=labels, autopct='%1.1f%%')
        plt.title(title)
    
    elif chart_type == 'line':
        dates = [item['date'] for item in data]
        values = [item['value'] for item in data]
        plt.plot(dates, values, marker='o')
        plt.title(title)
        plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # Сохраняем в байтовый поток
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    # Кодируем в base64
    graphic = base64.b64encode(image_png).decode('utf-8')
    plt.close()
    
    return graphic