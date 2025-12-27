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
    if request.user.groups.filter(name='Родители').exists():
        if hasattr(request.user, 'parent_profile'):
            parent = request.user.parent_profile
            children = parent.studentparent_set.select_related('student').all()
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
        return redirect('reports_selector')
    elif request.user.groups.filter(name='Заведующие').exists() or request.user.is_superuser:
        return redirect('reports_selector')
    return redirect('home')
@login_required
def generate_report_view(request, report_type):
    filters = request.GET.dict()
    thread = get_report_data_threaded(request.user, report_type, filters)
    thread.join(timeout=5)
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
            if report_data['data']:
                headers = report_data['data'][0].keys()
                writer.writerow(headers)
                for row in report_data['data']:
                    writer.writerow(row.values())
            return response
    context = {
        'report_type': report_type,
        'report_data': report_data,
        'filters': filters
    }
    return render(request, 'kindergarten/report_result.html', context)

@login_required
def api_dashboard_data(request):
    if request.user.groups.filter(name='Заведующие').exists() or request.user.is_superuser:
        today = date.today()
        data = {
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
            'age_chart': {
                'labels': [],
                'datasets': [{
                    'label': 'Количество детей',
                    'data': [],
                    'backgroundColor': ['#007bff', '#6610f2', '#6f42c1', '#e83e8c', '#fd7e14']
                }]
            },
            'capacity_chart': {
                'labels': [],
                'datasets': [{
                    'label': 'Наполняемость (%)',
                    'data': [],
                    'backgroundColor': '#20c997'
                }]
            },
            'group_stats': []
        }
        for i in range(7):
            day = today - timedelta(days=i)
            present = Attendance.objects.filter(attendance_date=day, status=True).count()
            absent = Attendance.objects.filter(attendance_date=day, status=False).count()
            data['attendance_chart']['labels'].insert(0, day.strftime('%d.%m'))
            data['attendance_chart']['datasets'][0]['data'].insert(0, present)
            data['attendance_chart']['datasets'][1]['data'].insert(0, absent)
        age_groups = ['2-3 года', '3-4 года', '4-5 лет', '5-6 лет', '6-7 лет']
        for age_group in age_groups:
            count = Student.objects.filter(
                student_date_out__isnull=True,
                student_birthday__lte=date.today() - timedelta(days=int(age_group.split('-')[0])*365),
                student_birthday__gt=date.today() - timedelta(days=int(age_group.split('-')[1].split()[0])*365)
            ).count()
            data['age_chart']['labels'].append(age_group)
            data['age_chart']['datasets'][0]['data'].append(count)
        for group in Group.objects.all():
            current = group.current_students_count()
            capacity = Group.MAX_STUDENTS
            percentage = round(current / capacity * 100, 1) if capacity > 0 else 0
            data['capacity_chart']['labels'].append(group.group_name)
            data['capacity_chart']['datasets'][0]['data'].append(percentage)
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
@login_required
def parent_reports(request):
    if not request.user.groups.filter(name='Родители').exists():
        messages.error(request, 'Доступ запрещен')
        return redirect('home')
    if not hasattr(request.user, 'parent_profile'):
        messages.error(request, 'Профиль родителя не найден')
        return redirect('home')
    parent = request.user.parent_profile
    children_relations = StudentParent.objects.filter(
        parent=parent
    ).select_related('student', 'student__group', 'student__group__teacher')
    children = []
    for relation in children_relations:
        student = relation.student
        children.append({
            'id': student.pk,
            'fio': student.student_fio,
            'age': student.age(),
            'group': student.group.group_name if student.group else 'Не назначена',
            'relationship': relation.relationship_type
        })
    child_id_param = request.GET.get('child_id')
    report_data = None
    child_id = None
    if child_id_param:
        try:
            from .security import sanitize_integer
            child_id = sanitize_integer(child_id_param, min_value=1)
            if child_id is None:
                raise ValueError('Неверный ID ребенка')
            if not StudentParent.objects.filter(parent=parent, student_id=child_id).exists():
                messages.error(request, 'Доступ к данным этого ребенка запрещен')
            else:
                from .reports_utils import generate_parent_child_reports_threaded
                result = generate_parent_child_reports_threaded(child_id)
                if result['status'] == 'completed':
                    report_data = result['data']
                else:
                    messages.error(request, f'Ошибка при генерации отчета: {result.get("error", "Неизвестная ошибка")}')
        except (ValueError, Student.DoesNotExist):
            messages.error(request, 'Неверный ID ребенка')
            child_id = None
    context = {
        'children': children,
        'selected_child_id': child_id,
        'report_data': report_data
    }
    return render(request, 'kindergarten/parent_reports.html', context)
@login_required
def teacher_students_report(request):
    if not request.user.groups.filter(name='Воспитатели').exists():
        messages.error(request, 'Доступ запрещен')
        return redirect('home')
    if not hasattr(request.user, 'teacher_profile'):
        messages.error(request, 'Профиль воспитателя не найден')
        return redirect('home')
    teacher = request.user.teacher_profile
    from .reports_utils import generate_teacher_students_with_parents
    def worker():
        return generate_teacher_students_with_parents(teacher.pk)
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    report_data = generate_teacher_students_with_parents(teacher.pk)
    if report_data is None:
        messages.error(request, 'Ошибка при генерации отчета')
        return redirect('reports_dashboard')
    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="students_with_parents_{date.today()}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Группа', 'ФИО ученика', 'Дата рождения', 'Возраст', 'Дата поступления', 
                        'ФИО родителя', 'Степень родства', 'Телефон'])
        for group_data in report_data['groups_data']:
            for student in group_data['students']:
                for parent in student['parents']:
                    writer.writerow([
                        group_data['group_name'],
                        student['fio'],
                        student['birthday'],
                        student['age'],
                        student['date_in'],
                        parent['fio'],
                        parent['relationship'],
                        parent['phone']
                    ])
        return response
    context = {
        'report_data': report_data
    }
    return render(request, 'kindergarten/teacher_students_report.html', context)
@login_required
@user_passes_test(is_director_or_superuser)
def reports_dashboard_admin(request):
    from .reports_utils import generate_admin_dashboard
    
    def worker():
        return generate_admin_dashboard()
    
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    
    dashboard_data = generate_admin_dashboard()
    
    if dashboard_data is None:
        messages.error(request, 'Ошибка при генерации дашборда')
        return redirect('home')
    
    context = {
        'dashboard_data': dashboard_data
    }
    
    return render(request, 'kindergarten/reports_dashboard_admin.html', context)

@login_required
@user_passes_test(is_teacher_director_or_superuser)
def reports_selector(request):
    """Unified report selector for all roles"""
    # Determine user role and available options
    is_teacher = request.user.groups.filter(name='Воспитатели').exists()
    is_director = request.user.groups.filter(name='Заведующие').exists()
    is_admin = request.user.is_superuser
    
    # Get available groups and students based on role
    if is_teacher and hasattr(request.user, 'teacher_profile'):
        teacher = request.user.teacher_profile
        groups = Group.objects.filter(teacher=teacher).order_by('group_name')
        students = Student.objects.filter(group__teacher=teacher).order_by('student_fio')
        teachers = Teacher.objects.filter(pk=teacher.pk).annotate(groups_count=Count('group'))  # Only self
    else:  # Director or Admin
        groups = Group.objects.all().order_by('group_name')
        students = Student.objects.all().order_by('student_fio')
        teachers = Teacher.objects.all().annotate(groups_count=Count('group')).order_by('teacher_fio')
    
    context = {
        'groups': groups,
        'students': students,
        'teachers': teachers,
        'is_teacher': is_teacher,
        'is_director': is_director,
        'is_admin': is_admin,
    }
    
    return render(request, 'kindergarten/reports_selector.html', context)

@login_required
@user_passes_test(is_teacher_director_or_superuser)
def admin_group_report(request):
    if request.user.groups.filter(name='Воспитатели').exists():
        if hasattr(request.user, 'teacher_profile'):
            teacher = request.user.teacher_profile
            groups = Group.objects.filter(teacher=teacher).order_by('group_name')
        else:
            groups = Group.objects.none()
    else:
        groups = Group.objects.all().order_by('group_name')
    group_id_param = request.GET.get('group_id')
    report_data = None
    selected_group_id = None
    if group_id_param:
        try:
            from .security import sanitize_integer
            group_id = sanitize_integer(group_id_param, min_value=1)
            if group_id is None:
                raise ValueError('Неверный ID группы')
            selected_group_id = group_id
            from .reports_utils import generate_admin_group_report
            def worker():
                return generate_admin_group_report(group_id)
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()
            report_data = generate_admin_group_report(group_id)
            if report_data is None:
                messages.error(request, 'Группа не найдена')
        except (ValueError, Group.DoesNotExist):
            messages.error(request, 'Неверный ID группы')
    if request.GET.get('format') == 'csv' and report_data:
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="group_report_{group_id}_{date.today()}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Отчет по группе:', report_data['group_info']['name']])
        writer.writerow(['Категория:', report_data['group_info']['category']])
        writer.writerow(['Воспитатель:', report_data['group_info']['teacher']['fio']])
        writer.writerow(['Максимальная вместимость:', report_data['group_info']['max_capacity']])
        writer.writerow([])
        writer.writerow(['Статистика группы'])
        writer.writerow(['Всего учеников:', report_data['statistics']['total_students']])
        writer.writerow(['Заполненность (%):', report_data['statistics']['fill_percentage']])
        writer.writerow(['Средняя посещаемость (%):', report_data['statistics']['avg_attendance_percentage']])
        writer.writerow([])
        writer.writerow(['ФИО ученика', 'Дата рождения', 'Возраст', 'Дата поступления', 
                        'Присутствовал (дней)', 'Отсутствовал (дней)', 'Посещаемость (%)',
                        'ФИО родителя', 'Степень родства', 'Телефон'])
        for student in report_data['students']:
            first_parent = True
            for parent in student['parents']:
                if first_parent:
                    writer.writerow([
                        student['fio'],
                        student['birthday'],
                        student['age'],
                        student['date_in'],
                        student['attendance']['present'],
                        student['attendance']['absent'],
                        student['attendance']['percentage'],
                        parent['fio'],
                        parent['relationship'],
                        parent['phone']
                    ])
                    first_parent = False
                else:
                    writer.writerow([
                        '', '', '', '', '', '', '',
                        parent['fio'],
                        parent['relationship'],
                        parent['phone']
                    ])
            if not student['parents']:
                writer.writerow([
                    student['fio'],
                    student['birthday'],
                    student['age'],
                    student['date_in'],
                    student['attendance']['present'],
                    student['attendance']['absent'],
                    student['attendance']['percentage'],
                    'Нет данных', '', ''
                ])
        return response
    context = {
        'groups': groups,
        'selected_group_id': selected_group_id,
        'report_data': report_data
    }
    return render(request, 'kindergarten/admin_group_report.html', context)
@login_required
@user_passes_test(is_teacher_director_or_superuser)
def teacher_all_groups_report(request):
    """Report for all groups of a teacher (or selected teacher for director/admin)"""
    # Determine user role
    is_teacher = request.user.groups.filter(name='Воспитатели').exists()
    is_director = request.user.groups.filter(name='Заведующие').exists()
    is_admin = request.user.is_superuser
    
    # Get teacher_id from request or from user profile
    teacher_id_param = request.GET.get('teacher_id')
    
    if is_teacher and hasattr(request.user, 'teacher_profile'):
        # Teacher can only view their own groups
        teacher_id = request.user.teacher_profile.pk
    elif (is_director or is_admin) and teacher_id_param:
        # Director/Admin can view any teacher's groups
        try:
            from .security import sanitize_integer
            teacher_id = sanitize_integer(teacher_id_param, min_value=1)
            if teacher_id is None:
                messages.error(request, 'Неверный ID воспитателя')
                return redirect('reports_selector')
        except (ValueError, Teacher.DoesNotExist):
            messages.error(request, 'Неверный ID воспитателя')
            return redirect('reports_selector')
    else:
        messages.error(request, 'Необходимо выбрать воспитателя')
        return redirect('reports_selector')
    
    from .reports_utils import generate_teacher_all_groups_report
    
    def worker():
        return generate_teacher_all_groups_report(teacher_id)
    
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    
    report_data = generate_teacher_all_groups_report(teacher_id)
    
    if report_data is None:
        messages.error(request, 'Воспитатель не найден')
        return redirect('reports_selector')
    
    # CSV Export
    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="teacher_groups_report_{teacher_id}_{date.today()}.csv"'
        response.write('\ufeff')
        
        writer = csv.writer(response)
        writer.writerow(['Отчет по воспитателю:', report_data['teacher_info']['fio']])
        writer.writerow(['Должность:', report_data['teacher_info']['position']])
        writer.writerow([])
        
        writer.writerow(['Общая статистика'])
        writer.writerow(['Всего групп:', report_data['overall_statistics']['total_groups']])
        writer.writerow(['Всего учеников:', report_data['overall_statistics']['total_students']])
        writer.writerow(['Общая вместимость:', report_data['overall_statistics']['total_capacity']])
        writer.writerow(['Средняя заполненность (%):', report_data['overall_statistics']['avg_fill_percentage']])
        writer.writerow(['Средняя посещаемость (%):', report_data['overall_statistics']['avg_attendance_percentage']])
        writer.writerow([])
        
        writer.writerow(['Группы'])
        writer.writerow(['Название группы', 'Категория', 'Учеников', 'Вместимость', 
                        'Заполненность (%)', 'Присутствовало (месяц)', 'Отсутствовало (месяц)', 
                        'Посещаемость (%)'])
        
        for group in report_data['groups_data']:
            writer.writerow([
                group['name'],
                group['category'],
                group['students_count'],
                group['max_capacity'],
                group['fill_percentage'],
                group['attendance_present'],
                group['attendance_absent'],
                group['attendance_percentage']
            ])
        
        return response
    
    context = {
        'report_data': report_data,
        'is_teacher': is_teacher,
        'is_director': is_director,
        'is_admin': is_admin,
    }
    
    return render(request, 'kindergarten/teacher_all_groups_report.html', context)

@login_required
@user_passes_test(is_teacher_director_or_superuser)
def student_individual_report(request, student_id):
    from .models import Student
    try:
        student = Student.objects.select_related('group', 'group__teacher').get(pk=student_id)
        if request.user.groups.filter(name='Воспитатели').exists():
            if hasattr(request.user, 'teacher_profile'):
                teacher = request.user.teacher_profile
                if student.group and student.group.teacher != teacher:
                    messages.error(request, 'Доступ к данным этого ученика запрещен')
                    return redirect('admin_group_report')
        from .reports_utils import generate_parent_child_reports_threaded
        result = generate_parent_child_reports_threaded(student_id)
        if result['status'] == 'completed':
            report_data = result['data']
        else:
            messages.error(request, f'Ошибка при генерации отчета: {result.get("error", "Неизвестная ошибка")}')
            return redirect('admin_group_report')
        context = {
            'report_data': report_data,
            'is_staff_view': True,
        }
        return render(request, 'kindergarten/student_individual_report.html', context)
    except Student.DoesNotExist:
        messages.error(request, 'Ученик не найден')
        return redirect('admin_group_report')
