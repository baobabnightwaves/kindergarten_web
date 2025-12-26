from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Prefetch
from datetime import date
from .models import Student, Teacher, Group, Parent, Attendance, StudentParent
@login_required
def home_optimized(request):
    today = date.today()
    from django.db.models import Count, Q
    attendance_stats = Attendance.objects.filter(attendance_date=today).aggregate(
        present=Count('pk', filter=Q(status=True)),
        absent=Count('pk', filter=Q(status=False))
    )
    context = {
        'total_groups': Group.objects.count(),
        'total_students': Student.objects.filter(student_date_out__isnull=True).count(),
        'total_teachers': Teacher.objects.count(),
        'total_parents': Parent.objects.count(),
        'attendance_today': attendance_stats['present'] or 0,
        'absent_today': attendance_stats['absent'] or 0,
    }
    return render(request, 'kindergarten/home.html', context)
@login_required
def student_detail_optimized(request, pk):
    student = get_object_or_404(
        Student.objects.select_related('group', 'group__teacher'), 
        pk=pk
    )
    parents = StudentParent.objects.filter(student=student).select_related(
        'parent', 'parent__user'
    )
    attendance = Attendance.objects.filter(student=student).select_related(
        'noted_by'
    ).order_by('-attendance_date')[:10]
    return render(request, 'kindergarten/student_detail.html', {
        'student': student,
        'parents': parents,
        'attendance': attendance,
        'age': student.age(),
    })
@login_required
def group_detail_optimized(request, pk):
    group = get_object_or_404(
        Group.objects.select_related('teacher', 'teacher__user'), 
        pk=pk
    )
    students = Student.objects.filter(group=group).prefetch_related(
        Prefetch(
            'attendance_set',
            queryset=Attendance.objects.filter(attendance_date=date.today()).select_related('noted_by'),
            to_attr='today_attendance'
        )
    )
    attendance_today = Attendance.objects.filter(
        student__group=group,
        attendance_date=date.today()
    ).select_related('student', 'noted_by')
    return render(request, 'kindergarten/group_detail.html', {
        'group': group,
        'students': students,
        'students_count': students.count(),
        'attendance_today': attendance_today,
    })
@login_required
def parent_list_optimized(request):
    parents = Parent.objects.select_related('user').all()
    if request.user.groups.filter(name='Воспитатели').exists() and hasattr(request.user, 'teacher_profile'):
        teacher = request.user.teacher_profile
        parent_ids = StudentParent.objects.filter(
            student__group__teacher=teacher
        ).values_list('parent_id', flat=True).distinct()
        parents = parents.filter(pk__in=parent_ids)
    return render(request, 'kindergarten/parent_list.html', {
        'parents': parents,
    })
@login_required
def parent_detail_optimized(request, pk):
    parent = get_object_or_404(Parent.objects.select_related('user'), pk=pk)
    children = StudentParent.objects.filter(parent=parent).select_related(
        'student', 
        'student__group', 
        'student__group__teacher'
    )
    return render(request, 'kindergarten/parent_detail.html', {
        'parent': parent,
        'children': children,
    })
@login_required
def student_list_optimized(request):
    students = Student.objects.select_related('group', 'group__teacher').all()
    if request.user.groups.filter(name='Воспитатели').exists() and hasattr(request.user, 'teacher_profile'):
        teacher = request.user.teacher_profile
        students = students.filter(group__teacher=teacher)
    search_query = request.GET.get('search', '')
    group_filter = request.GET.get('group', '')
    status_filter = request.GET.get('status', '')
    if search_query:
        students = students.filter(student_fio__icontains=search_query)
    if group_filter:
        students = students.filter(group_id=group_filter)
        selected_group = get_object_or_404(Group, pk=group_filter)
    else:
        selected_group = None
    if status_filter == 'active':
        students = students.filter(student_date_out__isnull=True)
    elif status_filter == 'graduated':
        students = students.filter(student_date_out__isnull=False)
    if request.user.groups.filter(name='Воспитатели').exists() and hasattr(request.user, 'teacher_profile'):
        teacher = request.user.teacher_profile
        groups = Group.objects.filter(teacher=teacher)
    elif request.user.groups.filter(name='Заведующие').exists() or request.user.is_superuser:
        groups = Group.objects.all()
    else:
        groups = Group.objects.none()
    students = students.order_by('student_fio')
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(students, 25)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    return render(request, 'kindergarten/student_list.html', {
        'students': page_obj,
        'groups': groups,
        'selected_group': selected_group,
    })
@login_required
def api_stats_optimized(request):
    from django.http import JsonResponse
    from datetime import timedelta
    today = date.today()
    attendance_stats = Attendance.objects.filter(attendance_date=today).aggregate(
        present=Count('pk', filter=Q(status=True)),
        absent=Count('pk', filter=Q(status=False))
    )
    stats = {
        'total_students': Student.objects.filter(student_date_out__isnull=True).count(),
        'total_teachers': Teacher.objects.count(),
        'total_groups': Group.objects.count(),
        'total_parents': Parent.objects.count(),
        'attendance_today': attendance_stats['present'] or 0,
        'absent_today': attendance_stats['absent'] or 0,
    }
    groups = Group.objects.select_related('teacher').annotate(
        students_count=Count('student', filter=Q(student__student_date_out__isnull=True))
    )
    groups_stats = []
    for group in groups:
        groups_stats.append({
            'name': group.group_name,
            'students_count': group.students_count,
            'available': group.max_capacity - group.students_count,
            'is_full': group.students_count >= group.max_capacity,
            'category': group.group_category,
        })
    stats['groups_stats'] = groups_stats
    seven_days_ago = today - timedelta(days=6)
    attendance_records = Attendance.objects.filter(
        attendance_date__gte=seven_days_ago,
        attendance_date__lte=today
    ).values('attendance_date', 'status').annotate(count=Count('pk'))
    attendance_by_date = {}
    for record in attendance_records:
        date_key = record['attendance_date']
        if date_key not in attendance_by_date:
            attendance_by_date[date_key] = {'present': 0, 'absent': 0}
        if record['status']:
            attendance_by_date[date_key]['present'] = record['count']
        else:
            attendance_by_date[date_key]['absent'] = record['count']
    attendance_data = []
    attendance_labels = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_stats = attendance_by_date.get(day, {'present': 0, 'absent': 0})
        total = day_stats['present'] + day_stats['absent']
        attendance_labels.append(day.strftime('%d.%m'))
        if total > 0:
            attendance_data.append(round((day_stats['present'] / total) * 100, 1))
        else:
            attendance_data.append(0)
    stats['attendance_data'] = attendance_data
    stats['attendance_labels'] = attendance_labels
    return JsonResponse(stats)
