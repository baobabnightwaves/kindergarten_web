import threading
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import date, timedelta
from django.db.models import Count, Sum, Avg, Q, F
from django.db import connection
from collections import defaultdict
import json
import calendar
def get_report_data_threaded(user, report_type, filters=None):
    if filters is None:
        filters = {}
    thread = threading.Thread(
        target=generate_report_data,
        args=(user, report_type, filters)
    )
    thread.daemon = True
    thread.start()
    return thread
def generate_report_data(user, report_type, filters):
    from .models import Student, Teacher, Group, Parent, Attendance, StudentParent
    try:
        if user.groups.filter(name='Родители').exists():
            if hasattr(user, 'parent_profile'):
                parent = user.parent_profile
                child_ids = parent.studentparent_set.values_list('student_id', flat=True)
                return get_parent_report_data(parent, child_ids, report_type, filters)
        elif user.groups.filter(name='Воспитатели').exists():
            if hasattr(user, 'teacher_profile'):
                teacher = user.teacher_profile
                teacher_groups = Group.objects.filter(teacher=teacher)
                return get_teacher_report_data(teacher, teacher_groups, report_type, filters)
        elif user.groups.filter(name='Заведующие').exists() or user.is_superuser:
            return get_admin_report_data(user, report_type, filters)
    except Exception as e:
        print(f"Ошибка при генерации отчета: {e}")
        return None
def get_parent_report_data(parent, child_ids, report_type, filters):
    from .models import Student, Attendance, Group
    children = Student.objects.filter(pk__in=child_ids)
    if report_type == 'attendance_by_month':
        data = []
        for child in children:
            from django.db.models.functions import ExtractMonth
            attendance_by_month = Attendance.objects.filter(
                student=child,
                attendance_date__year=date.today().year
            ).annotate(
                month=ExtractMonth('attendance_date')
            ).values('month').annotate(
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
    from .models import Student, Attendance, Group
    group_ids = teacher_groups.values_list('pk', flat=True)
    students = Student.objects.filter(group_id__in=group_ids)
    if report_type == 'group_attendance':
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
    from .models import Student, Teacher, Group, Parent, Attendance
    if report_type == 'overall_stats':
        today = date.today()
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
        from django.db.models.functions import ExtractYear
        current_year = date.today().year
        age_stats = Student.objects.filter(
            student_date_out__isnull=True
        ).annotate(
            birth_year=ExtractYear('student_birthday')
        ).annotate(
            age=current_year - F('birth_year')
        ).values('age').annotate(
            count=Count('pk')
        ).order_by('age')
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
        ).order_by('-attendance_date')[:100]
        return {
            'type': 'table',
            'title': 'Детальная посещаемость',
            'data': list(attendance_data)
        }
    elif report_type == 'financial_report':
        financial_data = []
        for group in Group.objects.all():
            students_count = group.current_students_count()
            monthly_revenue = students_count * 10000
            financial_data.append({
                'group': group.group_name,
                'students_count': students_count,
                'monthly_revenue': monthly_revenue,
                'yearly_revenue': monthly_revenue * 12,
                'teacher_salary': 50000 if group.teacher else 0,
                'net_profit': monthly_revenue - (50000 if group.teacher else 0)
            })
        return {
            'type': 'table',
            'title': 'Финансовый отчет по группам',
            'data': financial_data
        }
def create_chart(chart_type, data, title):
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
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    graphic = base64.b64encode(image_png).decode('utf-8')
    plt.close()
    return graphic
def generate_parent_child_reports_threaded(child_id):
    result = {'status': 'processing', 'data': None}
    def worker():
        try:
            result['data'] = generate_parent_child_reports(child_id)
            result['status'] = 'completed'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    return result
def generate_parent_child_reports(child_id):
    from .models import Student, Attendance, Group
    try:
        child = Student.objects.select_related('group', 'group__teacher').get(pk=child_id)
        group = child.group
        calendar_data = get_child_attendance_calendar(child)
        if group:
            group_students_attendance = get_group_students_attendance_percentage(group)
            group_attendance_chart = get_group_attendance_chart_30days(group)
        else:
            group_students_attendance = []
            group_attendance_chart = {}
        return {
            'child': {
                'id': child.pk,
                'fio': child.student_fio,
                'birthday': child.student_birthday,
                'age': child.age(),
                'group_id': group.pk if group else None,
                'group_name': group.group_name if group else 'Не назначена',
                'teacher_name': group.teacher.teacher_fio if group and group.teacher else 'Не назначен'
            },
            'calendar_data': calendar_data,
            'group_students_attendance': group_students_attendance,
            'group_attendance_chart': group_attendance_chart
        }
    except Student.DoesNotExist:
        return None
def get_child_attendance_calendar(child):
    from .models import Attendance
    end_date = date.today()
    start_date = end_date - timedelta(days=29)
    attendances = Attendance.objects.filter(
        student=child,
        attendance_date__range=[start_date, end_date]
    ).order_by('attendance_date')
    attendance_dict = {
        att.attendance_date: {
            'status': att.status,
            'reason': att.reason
        }
        for att in attendances
    }
    calendar_data = []
    current_date = start_date
    while current_date <= end_date:
        is_weekend = current_date.weekday() >= 5
        day_data = {
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': current_date.strftime('%A'),
            'day_num': current_date.day,
            'is_weekend': is_weekend,
        }
        if current_date in attendance_dict:
            att_data = attendance_dict[current_date]
            if att_data['status']:
                day_data['status'] = 'present'
                day_data['reason'] = ''
            else:
                reason_lower = att_data['reason'].lower() if att_data['reason'] else ''
                if 'болезн' in reason_lower or 'болел' in reason_lower or 'болен' in reason_lower:
                    day_data['status'] = 'sick'
                else:
                    day_data['status'] = 'absent'
                day_data['reason'] = att_data['reason']
        else:
            if is_weekend:
                day_data['status'] = 'weekend'
                day_data['reason'] = ''
            else:
                day_data['status'] = 'no_data'
                day_data['reason'] = ''
        calendar_data.append(day_data)
        current_date += timedelta(days=1)
    working_days = [d for d in calendar_data if not d['is_weekend']]
    total_days = len(working_days)
    present_days = len([d for d in working_days if d['status'] == 'present'])
    absent_days = len([d for d in working_days if d['status'] in ['absent', 'sick']])
    return {
        'days': calendar_data,
        'stats': {
            'total_days': total_days,
            'present_days': present_days,
            'absent_days': absent_days,
            'attendance_percentage': round((present_days / total_days * 100) if total_days > 0 else 0, 1)
        }
    }
def get_group_students_attendance_percentage(group):
    from .models import Student, Attendance
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    students = Student.objects.filter(
        group=group,
        student_date_out__isnull=True
    ).order_by('student_fio')
    students_data = []
    for student in students:
        attendance_stats = Attendance.objects.filter(
            student=student,
            attendance_date__range=[start_of_month, today]
        ).aggregate(
            present=Count('pk', filter=Q(status=True)),
            absent=Count('pk', filter=Q(status=False)),
            total=Count('pk')
        )
        present = attendance_stats['present'] or 0
        absent = attendance_stats['absent'] or 0
        total = attendance_stats['total'] or 0
        attendance_percentage = round((present / total * 100) if total > 0 else 0, 1)
        students_data.append({
            'id': student.pk,
            'fio': student.student_fio,
            'birthday': student.student_birthday,
            'age': student.age(),
            'present_days': present,
            'absent_days': absent,
            'total_days': total,
            'attendance_percentage': attendance_percentage
        })
    return students_data
def get_group_attendance_chart_30days(group):
    from .models import Attendance
    end_date = date.today()
    start_date = end_date - timedelta(days=29)
    daily_attendance = Attendance.objects.filter(
        student__group=group,
        attendance_date__range=[start_date, end_date]
    ).values('attendance_date').annotate(
        present=Count('pk', filter=Q(status=True)),
        absent=Count('pk', filter=Q(status=False)),
        total=Count('pk')
    ).order_by('attendance_date')
    attendance_by_date = {
        item['attendance_date']: item
        for item in daily_attendance
    }
    labels = []
    present_data = []
    absent_data = []
    percentage_data = []
    current_date = start_date
    while current_date <= end_date:
        labels.append(current_date.strftime('%d.%m'))
        if current_date in attendance_by_date:
            data = attendance_by_date[current_date]
            present = data['present']
            absent = data['absent']
            total = data['total']
            percentage = round((present / total * 100) if total > 0 else 0, 1)
        else:
            present = 0
            absent = 0
            percentage = 0
        present_data.append(present)
        absent_data.append(absent)
        percentage_data.append(percentage)
        current_date += timedelta(days=1)
    return {
        'labels': labels,
        'present': present_data,
        'absent': absent_data,
        'percentage': percentage_data
    }
def generate_teacher_students_with_parents(teacher_id):
    from .models import Teacher, Student, Parent, StudentParent
    try:
        teacher = Teacher.objects.get(pk=teacher_id)
        groups = teacher.group_set.all()
        report_data = []
        for group in groups:
            students = Student.objects.filter(
                group=group,
                student_date_out__isnull=True
            ).prefetch_related('studentparent_set__parent').order_by('student_fio')
            group_data = {
                'group_id': group.pk,
                'group_name': group.group_name,
                'group_category': group.get_group_category_display(),
                'students': []
            }
            for student in students:
                parent_relations = StudentParent.objects.filter(
                    student=student
                ).select_related('parent')
                parents_info = []
                for rel in parent_relations:
                    parent = rel.parent
                    parents_info.append({
                        'fio': parent.parent_fio,
                        'relationship': rel.relationship_type,
                        'phone': parent.parent_number
                    })
                student_data = {
                    'id': student.pk,
                    'fio': student.student_fio,
                    'birthday': student.student_birthday,
                    'age': student.age(),
                    'date_in': student.student_date_in,
                    'parents': parents_info
                }
                group_data['students'].append(student_data)
            report_data.append(group_data)
        return {
            'teacher': {
                'id': teacher.pk,
                'fio': teacher.teacher_fio,
                'position': teacher.teacher_position
            },
            'groups_data': report_data
        }
    except Teacher.DoesNotExist:
        return None
def generate_teacher_dashboard(teacher_id):
    from .models import Teacher, Student, Attendance
    try:
        teacher = Teacher.objects.get(pk=teacher_id)
        groups = teacher.group_set.all()
        today = date.today()
        start_of_month = date(today.year, today.month, 1)
        group_attendance_stats = []
        for group in groups:
            stats = Attendance.objects.filter(
                student__group=group,
                attendance_date__range=[start_of_month, today]
            ).aggregate(
                present=Count('pk', filter=Q(status=True)),
                absent=Count('pk', filter=Q(status=False)),
                total=Count('pk')
            )
            present = stats['present'] or 0
            total = stats['total'] or 0
            percentage = round((present / total * 100) if total > 0 else 0, 1)
            group_attendance_stats.append({
                'group_name': group.group_name,
                'present': present,
                'absent': stats['absent'] or 0,
                'percentage': percentage
            })
        end_date = today
        start_date = end_date - timedelta(days=29)
        daily_stats = Attendance.objects.filter(
            student__group__in=groups,
            attendance_date__range=[start_date, end_date]
        ).values('attendance_date').annotate(
            present=Count('pk', filter=Q(status=True)),
            total=Count('pk')
        ).order_by('attendance_date')
        attendance_by_date = {item['attendance_date']: item for item in daily_stats}
        labels = []
        attendance_percentages = []
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime('%d.%m'))
            if current_date in attendance_by_date:
                data = attendance_by_date[current_date]
                percentage = round((data['present'] / data['total'] * 100) if data['total'] > 0 else 0, 1)
            else:
                percentage = 0
            attendance_percentages.append(percentage)
            current_date += timedelta(days=1)
        students_low_attendance = []
        students = Student.objects.filter(
            group__in=groups,
            student_date_out__isnull=True
        )
        for student in students:
            stats = Attendance.objects.filter(
                student=student,
                attendance_date__range=[start_of_month, today]
            ).aggregate(
                present=Count('pk', filter=Q(status=True)),
                total=Count('pk')
            )
            present = stats['present'] or 0
            total = stats['total'] or 0
            percentage = round((present / total * 100) if total > 0 else 0, 1)
            if percentage < 70 and total > 0:
                students_low_attendance.append({
                    'fio': student.student_fio,
                    'group': student.group.group_name,
                    'attendance_percentage': percentage,
                    'present_days': present,
                    'total_days': total
                })
        students_low_attendance.sort(key=lambda x: x['attendance_percentage'])
        age_distribution = []
        for group in groups:
            students_count = Student.objects.filter(
                group=group,
                student_date_out__isnull=True
            ).count()
            age_distribution.append({
                'group_name': group.group_name,
                'category': group.get_group_category_display(),
                'students_count': students_count,
                'max_capacity': group.max_capacity,
                'fill_percentage': round((students_count / group.max_capacity * 100) if group.max_capacity > 0 else 0, 1)
            })
        total_students = Student.objects.filter(
            group__in=groups,
            student_date_out__isnull=True
        ).count()
        total_groups = groups.count()
        today_attendance = Attendance.objects.filter(
            student__group__in=groups,
            attendance_date=today
        ).aggregate(
            present=Count('pk', filter=Q(status=True)),
            total=Count('pk')
        )
        today_percentage = round(
            (today_attendance['present'] / today_attendance['total'] * 100) 
            if today_attendance['total'] and today_attendance['total'] > 0 else 0, 
            1
        )
        return {
            'teacher': {
                'id': teacher.pk,
                'fio': teacher.teacher_fio,
                'position': teacher.teacher_position
            },
            'key_metrics': {
                'total_students': total_students,
                'total_groups': total_groups,
                'today_present': today_attendance['present'] or 0,
                'today_total': today_attendance['total'] or 0,
                'today_percentage': today_percentage
            },
            'group_attendance_stats': group_attendance_stats,
            'attendance_trend': {
                'labels': labels,
                'data': attendance_percentages
            },
            'students_low_attendance': students_low_attendance,
            'age_distribution': age_distribution
        }
    except Teacher.DoesNotExist:
        return None
def generate_admin_group_report(group_id):
    from .models import Group, Student, Teacher, Attendance, StudentParent
    try:
        group = Group.objects.select_related('teacher').get(pk=group_id)
        group_info = {
            'id': group.pk,
            'name': group.group_name,
            'category': group.get_group_category_display(),
            'max_capacity': group.max_capacity,
            'teacher': {
                'id': group.teacher.pk if group.teacher else None,
                'fio': group.teacher.teacher_fio if group.teacher else 'Не назначен',
                'position': group.teacher.teacher_position if group.teacher else '',
                'phone': group.teacher.teacher_number if group.teacher else ''
            }
        }
        students = Student.objects.filter(
            group=group,
            student_date_out__isnull=True
        ).prefetch_related('studentparent_set__parent').order_by('student_fio')
        today = date.today()
        start_of_month = date(today.year, today.month, 1)
        students_data = []
        for student in students:
            parent_relations = StudentParent.objects.filter(
                student=student
            ).select_related('parent')
            parents_info = []
            for rel in parent_relations:
                parent = rel.parent
                parents_info.append({
                    'fio': parent.parent_fio,
                    'relationship': rel.relationship_type,
                    'phone': parent.parent_number
                })
            attendance_stats = Attendance.objects.filter(
                student=student,
                attendance_date__range=[start_of_month, today]
            ).aggregate(
                present=Count('pk', filter=Q(status=True)),
                absent=Count('pk', filter=Q(status=False)),
                total=Count('pk')
            )
            present = attendance_stats['present'] or 0
            absent = attendance_stats['absent'] or 0
            total = attendance_stats['total'] or 0
            percentage = round((present / total * 100) if total > 0 else 0, 1)
            students_data.append({
                'id': student.pk,
                'fio': student.student_fio,
                'birthday': student.student_birthday,
                'age': student.age(),
                'date_in': student.student_date_in,
                'parents': parents_info,
                'attendance': {
                    'present': present,
                    'absent': absent,
                    'total': total,
                    'percentage': percentage
                }
            })
        total_students = len(students_data)
        fill_percentage = round((total_students / group.max_capacity * 100) if group.max_capacity > 0 else 0, 1)
        avg_attendance = Attendance.objects.filter(
            student__group=group,
            attendance_date__range=[start_of_month, today]
        ).aggregate(
            present=Count('pk', filter=Q(status=True)),
            total=Count('pk')
        )
        avg_percentage = round(
            (avg_attendance['present'] / avg_attendance['total'] * 100) 
            if avg_attendance['total'] and avg_attendance['total'] > 0 else 0,
            1
        )
        chart_data = get_group_attendance_chart_30days(group)
        return {
            'group_info': group_info,
            'students': students_data,
            'statistics': {
                'total_students': total_students,
                'max_capacity': group.max_capacity,
                'fill_percentage': fill_percentage,
                'avg_attendance_percentage': avg_percentage,
                'avg_attendance_present': avg_attendance['present'] or 0,
                'avg_attendance_total': avg_attendance['total'] or 0
            },
            'chart_data': chart_data
        }
    except Group.DoesNotExist:
        return None
def generate_teacher_all_groups_report(teacher_id):
    """Generate report for all groups of a specific teacher"""
    from .models import Group, Student, Teacher, Attendance, StudentParent
    
    try:
        teacher = Teacher.objects.get(pk=teacher_id)
        groups = Group.objects.filter(teacher=teacher).order_by('group_name')
        
        if not groups.exists():
            return {
                'teacher_info': {
                    'id': teacher.pk,
                    'fio': teacher.teacher_fio,
                    'position': teacher.teacher_position,
                    'phone': teacher.teacher_number
                },
                'groups_data': [],
                'overall_statistics': {
                    'total_groups': 0,
                    'total_students': 0,
                    'total_capacity': 0,
                    'avg_fill_percentage': 0,
                    'avg_attendance_percentage': 0
                },
                'chart_data': {'labels': [], 'datasets': []}
            }
        
        today = date.today()
        start_of_month = date(today.year, today.month, 1)
        
        # Collect data for each group
        groups_data = []
        total_students = 0
        total_capacity = 0
        
        for group in groups:
            students = Student.objects.filter(
                group=group,
                student_date_out__isnull=True
            ).count()
            
            attendance_stats = Attendance.objects.filter(
                student__group=group,
                attendance_date__range=[start_of_month, today]
            ).aggregate(
                present=Count('pk', filter=Q(status=True)),
                absent=Count('pk', filter=Q(status=False)),
                total=Count('pk')
            )
            
            present = attendance_stats['present'] or 0
            total_att = attendance_stats['total'] or 0
            percentage = round((present / total_att * 100) if total_att > 0 else 0, 1)
            
            fill_percentage = round((students / group.max_capacity * 100) if group.max_capacity > 0 else 0, 1)
            
            groups_data.append({
                'id': group.pk,
                'name': group.group_name,
                'category': group.get_group_category_display(),
                'students_count': students,
                'max_capacity': group.max_capacity,
                'fill_percentage': fill_percentage,
                'attendance_present': present,
                'attendance_absent': attendance_stats['absent'] or 0,
                'attendance_total': total_att,
                'attendance_percentage': percentage
            })
            
            total_students += students
            total_capacity += group.max_capacity
        
        # Calculate overall statistics
        avg_fill = round((total_students / total_capacity * 100) if total_capacity > 0 else 0, 1)
        
        overall_attendance = Attendance.objects.filter(
            student__group__teacher=teacher,
            attendance_date__range=[start_of_month, today]
        ).aggregate(
            present=Count('pk', filter=Q(status=True)),
            total=Count('pk')
        )
        
        avg_attendance = round(
            (overall_attendance['present'] / overall_attendance['total'] * 100)
            if overall_attendance['total'] and overall_attendance['total'] > 0 else 0,
            1
        )
        
        # Generate chart data for last 30 days
        end_date = today
        start_date = end_date - timedelta(days=29)
        
        # Get daily attendance for all teacher's groups
        daily_stats = Attendance.objects.filter(
            student__group__teacher=teacher,
            attendance_date__range=[start_date, end_date]
        ).values('attendance_date').annotate(
            present=Count('pk', filter=Q(status=True)),
            absent=Count('pk', filter=Q(status=False)),
            total=Count('pk')
        ).order_by('attendance_date')
        
        attendance_by_date = {item['attendance_date']: item for item in daily_stats}
        
        labels = []
        present_data = []
        absent_data = []
        percentage_data = []
        
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime('%d.%m'))
            
            if current_date in attendance_by_date:
                data = attendance_by_date[current_date]
                present_data.append(data['present'])
                absent_data.append(data['absent'])
                percentage = round((data['present'] / data['total'] * 100) if data['total'] > 0 else 0, 1)
                percentage_data.append(percentage)
            else:
                present_data.append(0)
                absent_data.append(0)
                percentage_data.append(0)
            
            current_date += timedelta(days=1)
        
        return {
            'teacher_info': {
                'id': teacher.pk,
                'fio': teacher.teacher_fio,
                'position': teacher.teacher_position,
                'phone': teacher.teacher_number
            },
            'groups_data': groups_data,
            'overall_statistics': {
                'total_groups': len(groups_data),
                'total_students': total_students,
                'total_capacity': total_capacity,
                'avg_fill_percentage': avg_fill,
                'avg_attendance_percentage': avg_attendance,
                'month_present': overall_attendance['present'] or 0,
                'month_total': overall_attendance['total'] or 0
            },
            'chart_data': {
                'labels': labels,
                'present': present_data,
                'absent': absent_data,
                'percentage': percentage_data
            }
        }
    except Teacher.DoesNotExist:
        return None

def generate_admin_dashboard():
    from .models import Group, Student, Teacher, Parent, Attendance
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    total_students = Student.objects.filter(student_date_out__isnull=True).count()
    total_teachers = Teacher.objects.count()
    total_groups = Group.objects.count()
    total_parents = Parent.objects.count()
    today_attendance = Attendance.objects.filter(
        attendance_date=today
    ).aggregate(
        present=Count('pk', filter=Q(status=True)),
        absent=Count('pk', filter=Q(status=False)),
        total=Count('pk')
    )
    today_percentage = round(
        (today_attendance['present'] / today_attendance['total'] * 100)
        if today_attendance['total'] and today_attendance['total'] > 0 else 0,
        1
    )
    end_date = today
    start_date = end_date - timedelta(days=29)
    daily_stats = Attendance.objects.filter(
        attendance_date__range=[start_date, end_date]
    ).values('attendance_date').annotate(
        present=Count('pk', filter=Q(status=True)),
        total=Count('pk')
    ).order_by('attendance_date')
    attendance_by_date = {item['attendance_date']: item for item in daily_stats}
    labels_30days = []
    attendance_percentages_30days = []
    current_date = start_date
    while current_date <= end_date:
        labels_30days.append(current_date.strftime('%d.%m'))
        if current_date in attendance_by_date:
            data = attendance_by_date[current_date]
            percentage = round((data['present'] / data['total'] * 100) if data['total'] > 0 else 0, 1)
        else:
            percentage = 0
        attendance_percentages_30days.append(percentage)
        current_date += timedelta(days=1)
    age_distribution = []
    for group in Group.objects.all():
        students_count = Student.objects.filter(
            group=group,
            student_date_out__isnull=True
        ).count()
        if students_count > 0:
            age_distribution.append({
                'category': group.get_group_category_display(),
                'count': students_count
            })
    groups_fill = []
    for group in Group.objects.all():
        students_count = Student.objects.filter(
            group=group,
            student_date_out__isnull=True
        ).count()
        fill_percentage = round((students_count / group.max_capacity * 100) if group.max_capacity > 0 else 0, 1)
        groups_fill.append({
            'group_name': group.group_name,
            'students_count': students_count,
            'max_capacity': group.max_capacity,
            'fill_percentage': fill_percentage
        })
    groups_today_attendance = []
    for group in Group.objects.all():
        today_stats = Attendance.objects.filter(
            student__group=group,
            attendance_date=today
        ).aggregate(
            present=Count('pk', filter=Q(status=True)),
            absent=Count('pk', filter=Q(status=False)),
            total=Count('pk')
        )
        present = today_stats['present'] or 0
        total = today_stats['total'] or 0
        percentage = round((present / total * 100) if total > 0 else 0, 1)
        groups_today_attendance.append({
            'group_id': group.pk,
            'group_name': group.group_name,
            'teacher': group.teacher.teacher_fio if group.teacher else 'Не назначен',
            'present': present,
            'absent': today_stats['absent'] or 0,
            'total': total,
            'percentage': percentage
        })
    enrollments_by_month = []
    for month in range(1, 13):
        count = Student.objects.filter(
            student_date_in__year=today.year,
            student_date_in__month=month
        ).count()
        enrollments_by_month.append({
            'month': calendar.month_name[month][:3],
            'count': count
        })
    return {
        'key_metrics': {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_groups': total_groups,
            'total_parents': total_parents,
            'today_present': today_attendance['present'] or 0,
            'today_absent': today_attendance['absent'] or 0,
            'today_percentage': today_percentage
        },
        'attendance_trend_30days': {
            'labels': labels_30days,
            'data': attendance_percentages_30days
        },
        'age_distribution': age_distribution,
        'groups_fill': groups_fill,
        'groups_today_attendance': groups_today_attendance,
        'enrollments_by_month': enrollments_by_month
    }