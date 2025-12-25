# kindergarten/reports_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from datetime import date, timedelta, datetime
from django.db.models import Count, Q, Sum, Avg, F, When, Case, Value, IntegerField
import json
import csv
import threading
from io import StringIO

from .models import Student, Teacher, Group, Parent, Attendance, StudentParent
from .reports_utils import get_report_data_threaded, generate_report_data, create_chart

def is_director_or_superuser(user):
    return user.groups.filter(name='Заведующие').exists() or user.is_superuser

def is_teacher_director_or_superuser(user):
    return (
        user.groups.filter(name='Воспитатели').exists() or 
        user.groups.filter(name='Заведующие').exists() or 
        user.is_superuser
    )

@login_required
def reports_dashboard(request):
    """Дашборд с отчетами"""
    if request.user.groups.filter(name='Родители').exists():
        # Для родителя
        if hasattr(request.user, 'parent_profile'):
            parent = request.user.parent_profile
            children = parent.studentparent_set.select_related('student').all()
            
            # Данные для диаграмм
            child_data = []
            for relation in children:
                child = relation.student
                attendance_stats = Attendance.objects.filter(
                    student=child,
                    attendance_date__gte=date.today() - timedelta(days=30)
                ).aggregate(
                    present=Count('pk', filter=Q(status=True)),
                    absent=Count('pk', filter=Q(status=False))
                )
                
                child_data.append({
                    'name': child.student_fio,
                    'age': child.age(),
                    'group': child.group.group_name if child.group else 'Не назначена',
                    'present': attendance_stats['present'] or 0,
                    'absent': attendance_stats['absent'] or 0
                })
            
            context = {
                'user_type': 'parent',
                'children': child_data,
                'total_children': len(children)
            }
            return render(request, 'kindergarten/reports_dashboard_parent.html', context)
    
    elif request.user.groups.filter(name='Воспитатели').exists():
        # Для воспитателя
        if hasattr(request.user, 'teacher_profile'):
            teacher = request.user.teacher_profile
            groups = Group.objects.filter(teacher=teacher)
            students = Student.objects.filter(group__in=groups)
            
            # Статистика
            attendance_stats = Attendance.objects.filter(
                student__in=students,
                attendance_date__gte=date.today() - timedelta(days=30)
            ).aggregate(
                present=Count('pk', filter=Q(status=True)),
                absent=Count('pk', filter=Q(status=False))
            )
            
            group_stats = []
            for group in groups:
                students_count = group.current_students_count()
                group_attendance = Attendance.objects.filter(
                    student__group=group,
                    attendance_date=date.today()
                ).aggregate(
                    present=Count('pk', filter=Q(status=True)),
                    absent=Count('pk', filter=Q(status=False))
                )
                
                group_stats.append({
                    'name': group.group_name,
                    'students': students_count,
                    'present': group_attendance['present'] or 0,
                    'absent': group_attendance['absent'] or 0,
                    'attendance_rate': round(
                        (group_attendance['present'] or 0) / 
                        ((group_attendance['present'] or 0) + (group_attendance['absent'] or 0)) * 100, 1
                    ) if ((group_attendance['present'] or 0) + (group_attendance['absent'] or 0)) > 0 else 0
                })
            
            context = {
                'user_type': 'teacher',
                'teacher': teacher,
                'groups_count': groups.count(),
                'students_count': students.count(),
                'attendance_stats': attendance_stats,
                'group_stats': group_stats
            }
            return render(request, 'kindergarten/reports_dashboard_teacher.html', context)
    
    elif request.user.groups.filter(name='Заведующие').exists() or request.user.is_superuser:
        # Для администратора и суперпользователя
        # Получаем статистику для дашборда
        today = date.today()
        
        # 1. Общая статистика
        total_students = Student.objects.filter(student_date_out__isnull=True).count()
        total_teachers = Teacher.objects.count()
        total_groups = Group.objects.count()
        total_parents = Parent.objects.count()
        
        # 2. Посещаемость за последние 7 дней
        attendance_data = []
        for i in range(7):
            day = today - timedelta(days=i)
            present = Attendance.objects.filter(attendance_date=day, status=True).count()
            absent = Attendance.objects.filter(attendance_date=day, status=False).count()
            total = present + absent
            
            attendance_data.append({
                'date': day.strftime('%d.%m'),
                'present': present,
                'absent': absent,
                'rate': round(present / total * 100, 1) if total > 0 else 0
            })
        
        # 3. Распределение по возрастам
        age_distribution = Student.objects.filter(
            student_date_out__isnull=True
        ).extra({
            'age_group': """
                CASE 
                    WHEN (julianday('now') - julianday(student_birthday)) / 365.25 < 3 THEN '2-3 года'
                    WHEN (julianday('now') - julianday(student_birthday)) / 365.25 < 4 THEN '3-4 года'
                    WHEN (julianday('now') - julianday(student_birthday)) / 365.25 < 5 THEN '4-5 лет'
                    WHEN (julianday('now') - julianday(student_birthday)) / 365.25 < 6 THEN '5-6 лет'
                    ELSE '6-7 лет'
                END
            """
        }).values('age_group').annotate(
            count=Count('pk')
        ).order_by('age_group')
        
        # 4. Наполняемость групп
        group_capacity = []
        for group in Group.objects.all():
            current = group.current_students_count()
            capacity = group.max_capacity
            group_capacity.append({
                'name': group.group_name,
                'current': current,
                'capacity': capacity,
                'percentage': round(current / capacity * 100, 1) if capacity > 0 else 0
            })
        
        # 5. Посещаемость по группам за сегодня
        group_attendance_today = []
        for group in Group.objects.all():
            attendance = Attendance.objects.filter(
                student__group=group,
                attendance_date=today
            ).aggregate(
                present=Count('pk', filter=Q(status=True)),
                absent=Count('pk', filter=Q(status=False))
            )
            
            present = attendance['present'] or 0
            absent = attendance['absent'] or 0
            total = present + absent
            
            group_attendance_today.append({
                'group': group.group_name,
                'present': present,
                'absent': absent,
                'rate': round(present / total * 100, 1) if total > 0 else 0
            })
        
        context = {
            'user_type': 'admin',
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_groups': total_groups,
            'total_parents': total_parents,
            'attendance_data': attendance_data,
            'age_distribution': list(age_distribution),
            'group_capacity': group_capacity,
            'group_attendance_today': group_attendance_today,
            'groups': Group.objects.all(),
            'teachers': Teacher.objects.all(),
        }
        
        return render(request, 'kindergarten/reports_dashboard_admin.html', context)
    
    return redirect('home')

@login_required
def generate_report_view(request, report_type):
    """Генерация отчета по типу"""
    filters = request.GET.dict()
    
    # Запускаем генерацию отчета в отдельном потоке
    thread = get_report_data_threaded(request.user, report_type, filters)
    
    # Ждем завершения потока (в реальном приложении можно использовать Celery)
    thread.join(timeout=5)
    
    # Получаем данные
    report_data = generate_report_data(request.user, report_type, filters)
    
    if report_data is None:
        messages.error(request, 'Ошибка при генерации отчета')
        return redirect('reports_dashboard')
    
    if request.GET.get('format') == 'json':
        return JsonResponse(report_data)
    
    elif request.GET.get('format') == 'csv':
        if report_data['type'] == 'table':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="report_{report_type}_{date.today()}.csv"'
            
            writer = csv.writer(response)
            
            # Заголовки
            if report_data['data']:
                headers = report_data['data'][0].keys()
                writer.writerow(headers)
                
                # Данные
                for row in report_data['data']:
                    writer.writerow(row.values())
            
            return response
    
    # HTML представление
    context = {
        'report_type': report_type,
        'report_data': report_data,
        'filters': filters
    }
    
    return render(request, 'kindergarten/report_result.html', context)

@login_required
def report_builder(request):
    """Конструктор отчетов для администраторов"""
    if not (request.user.groups.filter(name='Заведующие').exists() or request.user.is_superuser):
        messages.error(request, 'Доступ запрещен')
        return redirect('home')
    
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        filters = {
            'start_date': request.POST.get('start_date'),
            'end_date': request.POST.get('end_date'),
            'group_id': request.POST.get('group_id'),
            'teacher_id': request.POST.get('teacher_id'),
            'format': request.POST.get('format', 'html')
        }
        
        # Удаляем пустые фильтры
        filters = {k: v for k, v in filters.items() if v}
        
        return redirect(f'{reverse("generate_report", args=[report_type])}?{request.POST.urlencode()}')
    
    context = {
        'groups': Group.objects.all(),
        'teachers': Teacher.objects.all(),
        'report_types': [
            ('overall_stats', 'Общая статистика'),
            ('detailed_attendance', 'Детальная посещаемость'),
            ('financial_report', 'Финансовый отчет'),
            ('group_attendance', 'Посещаемость по группам'),
            ('monthly_stats', 'Статистика по месяцам'),
        ]
    }
    
    return render(request, 'kindergarten/report_builder.html', context)

@login_required
def api_dashboard_data(request):
    """API для получения данных для дашборда"""
    if request.user.groups.filter(name='Заведующие').exists() or request.user.is_superuser:
        today = date.today()
        
        # Данные для диаграмм
        data = {
            # Диаграмма посещаемости за последние 7 дней
            'attendance_chart': {
                'labels': [],
                'datasets': [
                    {
                        'label': 'Присутствуют',
                        'data': [],
                        'backgroundColor': '#28a745'
                    },
                    {
                        'label': 'Отсутствуют',
                        'data': [],
                        'backgroundColor': '#dc3545'
                    }
                ]
            },
            
            # Диаграмма распределения по возрастам
            'age_chart': {
                'labels': [],
                'datasets': [{
                    'label': 'Количество детей',
                    'data': [],
                    'backgroundColor': ['#007bff', '#6610f2', '#6f42c1', '#e83e8c', '#fd7e14']
                }]
            },
            
            # Диаграмма наполняемости групп
            'capacity_chart': {
                'labels': [],
                'datasets': [{
                    'label': 'Наполняемость (%)',
                    'data': [],
                    'backgroundColor': '#20c997'
                }]
            },
            
            # Статистика по группам
            'group_stats': []
        }
        
        # Заполняем данные
        for i in range(7):
            day = today - timedelta(days=i)
            present = Attendance.objects.filter(attendance_date=day, status=True).count()
            absent = Attendance.objects.filter(attendance_date=day, status=False).count()
            
            data['attendance_chart']['labels'].insert(0, day.strftime('%d.%m'))
            data['attendance_chart']['datasets'][0]['data'].insert(0, present)
            data['attendance_chart']['datasets'][1]['data'].insert(0, absent)
        
        # Распределение по возрастам
        age_groups = ['2-3 года', '3-4 года', '4-5 лет', '5-6 лет', '6-7 лет']
        for age_group in age_groups:
            count = Student.objects.filter(
                student_date_out__isnull=True,
                student_birthday__lte=date.today() - timedelta(days=int(age_group.split('-')[0])*365),
                student_birthday__gt=date.today() - timedelta(days=int(age_group.split('-')[1].split()[0])*365)
            ).count()
            
            data['age_chart']['labels'].append(age_group)
            data['age_chart']['datasets'][0]['data'].append(count)
        
        # Наполняемость групп
        for group in Group.objects.all():
            current = group.current_students_count()
            capacity = group.max_capacity
            percentage = round(current / capacity * 100, 1) if capacity > 0 else 0
            
            data['capacity_chart']['labels'].append(group.group_name)
            data['capacity_chart']['datasets'][0]['data'].append(percentage)
            
            # Статистика по группе
            attendance_today = Attendance.objects.filter(
                student__group=group,
                attendance_date=today
            ).aggregate(
                present=Count('pk', filter=Q(status=True)),
                absent=Count('pk', filter=Q(status=False))
            )
            
            data['group_stats'].append({
                'name': group.group_name,
                'students': current,
                'capacity': capacity,
                'present': attendance_today['present'] or 0,
                'absent': attendance_today['absent'] or 0
            })
        
        return JsonResponse(data)
    
    return JsonResponse({'error': 'Доступ запрещен'}, status=403)