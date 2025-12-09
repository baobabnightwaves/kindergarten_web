from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from datetime import date, timedelta
import csv
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .models import Student, Teacher, Group, Parent, Attendance, StudentParent, Event
from .forms import StudentForm, TeacherForm, GroupForm, ParentForm, AttendanceForm, StudentParentForm, EventForm
from .forms import AddChildToParentForm, AddParentToChildForm  # Добавьте эти импорты

# ========== ГЛАВНАЯ СТРАНИЦА ==========
def home(request):
    """Главная страница со статистикой"""
    today = date.today()
    
    stats = {
        'total_students': Student.objects.filter(student_date_out__isnull=True).count(),
        'total_teachers': Teacher.objects.count(),
        'total_groups': Group.objects.count(),
        'total_parents': Parent.objects.count(),
        'attendance_today': Attendance.objects.filter(attendance_date=today, status=True).count(),
        'absent_today': Attendance.objects.filter(attendance_date=today, status=False).count(),
    }
    
    return render(request, 'kindergarten/home.html', {'stats': stats})

# ========== УЧЕНИКИ ==========
@login_required
def student_list(request):
    """Список учеников"""
    students = Student.objects.all().select_related('group')
    
    # Фильтрация
    group_filter = request.GET.get('group')
    status_filter = request.GET.get('status')
    
    if group_filter:
        students = students.filter(group_id=group_filter)
    if status_filter == 'active':
        students = students.filter(student_date_out__isnull=True)
    elif status_filter == 'graduated':
        students = students.filter(student_date_out__isnull=False)
    
    groups = Group.objects.all()
    return render(request, 'kindergarten/student_list.html', {
        'students': students,
        'groups': groups,
    })

@login_required
def student_detail(request, pk):
    """Детальная информация об ученике"""
    student = get_object_or_404(Student, pk=pk)
    parents = StudentParent.objects.filter(student=student).select_related('parent')
    attendance = Attendance.objects.filter(student=student).order_by('-attendance_date')[:10]
    
    return render(request, 'kindergarten/student_detail.html', {
        'student': student,
        'parents': parents,
        'attendance': attendance,
        'age': student.age(),
    })

@login_required
def student_create(request):
    """Создание нового ученика"""
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            try:
                student = form.save()
                messages.success(request, f'Ученик {student.student_fio} успешно добавлен!')
                return redirect('student_detail', pk=student.pk)
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = StudentForm()
    
    return render(request, 'kindergarten/student_form.html', {'form': form, 'title': 'Добавление ученика'})

@login_required
def student_edit(request, pk):
    """Редактирование ученика"""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Данные ученика {student.student_fio} обновлены!')
                return redirect('student_detail', pk=student.pk)
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = StudentForm(instance=student)
    
    return render(request, 'kindergarten/student_form.html', {'form': form, 'title': 'Редактирование ученика'})

@login_required
def student_delete(request, pk):
    """Удаление ученика"""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student_name = student.student_fio
        student.delete()
        messages.success(request, f'Ученик {student_name} удален!')
        return redirect('student_list')
    
    return render(request, 'kindergarten/student_confirm_delete.html', {'student': student})

# ========== ВОСПИТАТЕЛИ ==========
@login_required
def teacher_list(request):
    """Список воспитателей"""
    teachers = Teacher.objects.all()
    return render(request, 'kindergarten/teacher_list.html', {'teachers': teachers})

@login_required
def teacher_detail(request, pk):
    """Детальная информация о воспитателе"""
    teacher = get_object_or_404(Teacher, pk=pk)
    groups = Group.objects.filter(teacher=teacher)
    
    return render(request, 'kindergarten/teacher_detail.html', {
        'teacher': teacher,
        'groups': groups,
    })

@login_required
def teacher_create(request):
    """Создание нового воспитателя"""
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            teacher = form.save()
            messages.success(request, f'Воспитатель {teacher.teacher_fio} успешно добавлен!')
            return redirect('teacher_list')
    else:
        form = TeacherForm()
    
    return render(request, 'kindergarten/teacher_form.html', {'form': form, 'title': 'Добавление воспитателя'})

@login_required
def teacher_edit(request, pk):
    """Редактирование воспитателя"""
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, f'Данные воспитателя {teacher.teacher_fio} обновлены!')
            return redirect('teacher_detail', pk=teacher.pk)
    else:
        form = TeacherForm(instance=teacher)
    
    return render(request, 'kindergarten/teacher_form.html', {'form': form, 'title': 'Редактирование воспитателя'})

@login_required
def teacher_delete(request, pk):
    """Удаление воспитателя"""
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        teacher_name = teacher.teacher_fio
        teacher.delete()
        messages.success(request, f'Воспитатель {teacher_name} удален!')
        return redirect('teacher_list')
    
    return render(request, 'kindergarten/teacher_confirm_delete.html', {'teacher': teacher})

# ========== ГРУППЫ ==========
@login_required
def group_list(request):
    """Список групп с информацией о наполняемости"""
    groups = Group.objects.all().select_related('teacher')
    
    # Добавляем статистику для каждой группы
    for group in groups:
        group.current_count = group.current_students_count()
        group.available = group.available_places()
        group.is_full_flag = group.is_full()
    
    return render(request, 'kindergarten/group_list.html', {
        'groups': groups,
        'max_capacity': Group.MAX_STUDENTS,
    })

@login_required
def group_detail(request, pk):
    """Детальная информация о группе"""
    group = get_object_or_404(Group, pk=pk)
    students = Student.objects.filter(group=group)
    
    attendance_today = Attendance.objects.filter(
        student__in=students,
        attendance_date=date.today()
    )
    
    return render(request, 'kindergarten/group_detail.html', {
        'group': group,
        'students': students,
        'students_count': students.count(),
        'attendance_today': attendance_today,
    })

@login_required
def group_create(request):
    """Создание группы"""
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'Группа {group.group_name} успешно создана!')
            return redirect('group_detail', pk=group.pk)
    else:
        form = GroupForm()
    
    return render(request, 'kindergarten/group_form.html', {'form': form, 'title': 'Создание группы'})

@login_required
def group_edit(request, pk):
    """Редактирование группы"""
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, f'Группа {group.group_name} обновлена!')
            return redirect('group_detail', pk=group.pk)
    else:
        form = GroupForm(instance=group)
    
    return render(request, 'kindergarten/group_form.html', {'form': form, 'title': 'Редактирование группы'})

@login_required
def group_delete(request, pk):
    """Удаление группы"""
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        # Проверка: нельзя удалить группу с учениками
        if group.current_students_count() > 0:
            messages.error(request, f'Нельзя удалить группу с учениками! Сначала переведите учеников в другие группы.')
            return redirect('group_detail', pk=group.pk)
        
        group_name = group.group_name
        group.delete()
        messages.success(request, f'Группа {group_name} удалена!')
        return redirect('group_list')
    
    return render(request, 'kindergarten/group_confirm_delete.html', {'group': group})

# ========== РОДИТЕЛИ ==========
@login_required
def parent_list(request):
    """Список родителей"""
    parents = Parent.objects.all()
    return render(request, 'kindergarten/parent_list.html', {'parents': parents})

@login_required
def parent_detail(request, pk):
    """Детальная информация о родителе"""
    parent = get_object_or_404(Parent, pk=pk)
    children = StudentParent.objects.filter(parent=parent).select_related('student')
    
    return render(request, 'kindergarten/parent_detail.html', {
        'parent': parent,
        'children': children,
    })

@login_required
def parent_create(request):
    """Создание нового родителя"""
    if request.method == 'POST':
        form = ParentForm(request.POST)
        if form.is_valid():
            parent = form.save()
            messages.success(request, f'Родитель {parent.parent_fio} успешно добавлен!')
            return redirect('parent_list')
    else:
        form = ParentForm()
    
    return render(request, 'kindergarten/parent_form.html', {'form': form, 'title': 'Добавление родителя'})

@login_required
def parent_edit(request, pk):
    """Редактирование родителя"""
    parent = get_object_or_404(Parent, pk=pk)
    if request.method == 'POST':
        form = ParentForm(request.POST, instance=parent)
        if form.is_valid():
            form.save()
            messages.success(request, f'Данные родителя {parent.parent_fio} обновлены!')
            return redirect('parent_detail', pk=parent.pk)
    else:
        form = ParentForm(instance=parent)
    
    return render(request, 'kindergarten/parent_form.html', {'form': form, 'title': 'Редактирование родителя'})

@login_required
def parent_delete(request, pk):
    """Удаление родителя"""
    parent = get_object_or_404(Parent, pk=pk)
    if request.method == 'POST':
        parent_name = parent.parent_fio
        parent.delete()
        messages.success(request, f'Родитель {parent_name} удален!')
        return redirect('parent_list')
    
    return render(request, 'kindergarten/parent_confirm_delete.html', {'parent': parent})

# ========== СВЯЗИ РОДИТЕЛЬ-РЕБЕНОК ==========
@login_required
def add_child_to_parent(request, parent_id):
    """Добавление ребенка к родителю"""
    parent = get_object_or_404(Parent, pk=parent_id)
    
    if request.method == 'POST':
        form = AddChildToParentForm(request.POST, initial={'parent': parent})
        if form.is_valid():
            student = form.cleaned_data['student']
            relationship_type = form.cleaned_data['relationship_type']
            is_primary = form.cleaned_data['is_primary']
            
            # Проверяем, нет ли уже такой связи
            if not StudentParent.objects.filter(parent=parent, student=student).exists():
                StudentParent.objects.create(
                    parent=parent,
                    student=student,
                    relationship_type=relationship_type,
                    is_primary=is_primary
                )
                messages.success(request, f'Ребенок {student.student_fio} добавлен к родителю {parent.parent_fio}')
            else:
                messages.warning(request, 'Эта связь уже существует')
            
            return redirect('parent_detail', pk=parent_id)
    else:
        form = AddChildToParentForm(initial={'parent': parent})
    
    return render(request, 'kindergarten/add_child_to_parent.html', {
        'form': form,
        'parent': parent,
        'title': f'Добавление ребенка к родителю {parent.parent_fio}'
    })

@login_required
def add_parent_to_child(request, student_id):
    """Добавление родителя к ребенку"""
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        form = AddParentToChildForm(request.POST, initial={'student': student})
        if form.is_valid():
            parent = form.cleaned_data['parent']
            relationship_type = form.cleaned_data['relationship_type']
            is_primary = form.cleaned_data['is_primary']
            
            # Проверяем, нет ли уже такой связи
            if not StudentParent.objects.filter(parent=parent, student=student).exists():
                StudentParent.objects.create(
                    parent=parent,
                    student=student,
                    relationship_type=relationship_type,
                    is_primary=is_primary
                )
                messages.success(request, f'Родитель {parent.parent_fio} добавлен к ребенку {student.student_fio}')
            else:
                messages.warning(request, 'Эта связь уже существует')
            
            return redirect('student_detail', pk=student_id)
    else:
        form = AddParentToChildForm(initial={'student': student})
    
    return render(request, 'kindergarten/add_parent_to_child.html', {
        'form': form,
        'student': student,
        'title': f'Добавление родителя к ребенку {student.student_fio}'
    })

@login_required
def remove_parent_child_relation(request, relation_id):
    """Удаление связи родитель-ребенок"""
    relation = get_object_or_404(StudentParent, pk=relation_id)
    
    if request.method == 'POST':
        student_name = relation.student.student_fio
        parent_name = relation.parent.parent_fio
        relation.delete()
        
        messages.success(request, f'Связь между {parent_name} и {student_name} удалена')
        
        # Редирект обратно на страницу, откуда пришли
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('home')
    
    return render(request, 'kindergarten/remove_parent_child_confirm.html', {
        'relation': relation
    })

# ========== ПОСЕЩАЕМОСТЬ ==========
@login_required
def attendance_list(request):
    """Журнал посещаемости с фильтрацией по группе и дате"""
    today = date.today()
    
    # Получаем параметры фильтрации
    date_filter = request.GET.get('date', today.strftime('%Y-%m-%d'))
    group_filter = request.GET.get('group', '')
    
    try:
        filter_date = date.fromisoformat(date_filter)
    except (ValueError, TypeError):
        filter_date = today
    
    # Получаем все группы
    groups = Group.objects.all()
    
    # Получаем посещаемость с фильтрами
    attendance_query = Attendance.objects.filter(attendance_date=filter_date)
    
    if group_filter:
        attendance_query = attendance_query.filter(student__group_id=group_filter)
    
    attendance = attendance_query.select_related('student', 'student__group')
    
    # Получаем список учеников для выбранной группы
    students = Student.objects.filter(student_date_out__isnull=True)
    if group_filter:
        students = students.filter(group_id=group_filter)
    
    # Создаем словарь для быстрого доступа к посещаемости по student_id
    attendance_dict = {}
    for record in attendance:
        attendance_dict[record.student_id] = record
    
    # Создаем список студентов с их записями посещаемости
    students_with_attendance = []
    for student in students:
        attendance_record = attendance_dict.get(student.pk)
        students_with_attendance.append({
            'student': student,
            'attendance_record': attendance_record
        })
    
    return render(request, 'kindergarten/attendance_list.html', {
        'attendance': attendance,
        'students_with_attendance': students_with_attendance,
        'filter_date': filter_date,
        'group_filter': group_filter,
        'groups': groups,
        'today': today,
        'attendance_dict': attendance_dict,
    })

@login_required
def attendance_mark_bulk(request):
    """Массовая отметка посещаемости"""
    if request.method == 'POST':
        date_str = request.POST.get('date')
        group_id = request.POST.get('group_id')
        
        try:
            attendance_date = date.fromisoformat(date_str)
            
            # Получаем учеников выбранной группы
            students = Student.objects.filter(
                student_date_out__isnull=True,
                group_id=group_id
            )
            
            # Получаем текущего пользователя (воспитателя)
            teacher = None
            if request.user.is_authenticated and hasattr(request.user, 'teacher_profile'):
                teacher = request.user.teacher_profile
            
            # Обрабатываем каждую запись
            for student in students:
                status_key = f'status_{student.student_id}'
                reason_key = f'reason_{student.student_id}'
                
                if status_key in request.POST:
                    status = request.POST.get(status_key) == 'true'
                    reason = request.POST.get(reason_key, '')
                    
                    # Создаем или обновляем запись
                    Attendance.objects.update_or_create(
                        attendance_date=attendance_date,
                        student=student,
                        defaults={
                            'status': status,
                            'reason': reason if not status else '',
                            'noted_by': teacher,
                        }
                    )
            
            messages.success(request, f'Посещаемость за {attendance_date} сохранена!')
            return redirect(f"{reverse('attendance_list')}?date={date_str}&group={group_id}")
            
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('attendance_list')
    
    return redirect('attendance_list')

@login_required
def attendance_update(request, pk):
    """Обновление отдельной записи посещаемости"""
    if request.method == 'POST':
        attendance = get_object_or_404(Attendance, pk=pk)
        status = request.POST.get('status') == 'true'
        reason = request.POST.get('reason', '')
        
        attendance.status = status
        attendance.reason = reason
        attendance.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def attendance_create(request):
    """Создание записи о посещаемости"""
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save()
            messages.success(request, f'Запись о посещаемости создана!')
            return redirect('attendance_list')
    else:
        form = AttendanceForm()
    
    return render(request, 'kindergarten/attendance_form.html', {'form': form, 'title': 'Добавление посещаемости'})

@login_required
def attendance_edit(request, pk):
    """Редактирование посещаемости"""
    attendance = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            form.save()
            messages.success(request, f'Запись о посещаемости обновлена!')
            return redirect('attendance_list')
    else:
        form = AttendanceForm(instance=attendance)
    
    return render(request, 'kindergarten/attendance_form.html', {'form': form, 'title': 'Редактирование посещаемости'})

@login_required
def attendance_delete(request, pk):
    """Удаление посещаемости"""
    attendance = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        attendance.delete()
        messages.success(request, f'Запись о посещаемости удалена!')
        return redirect('attendance_list')
    
    return render(request, 'kindergarten/attendance_confirm_delete.html', {'attendance': attendance})

# ========== ОТЧЕТЫ ==========
@login_required
def reports(request):
    """Страница отчетов"""
    return render(request, 'kindergarten/reports.html')

@login_required
def generate_report(request, report_type):
    """Генерация отчетов"""
    from datetime import datetime
    
    if report_type == 'students_csv':
        # Экспорт учеников в CSV
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="students_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['ID', 'ФИО', 'Дата рождения', 'Возраст', 'Пол', 'Группа', 'Дата поступления', 'Дата выпуска', 'Статус'])
        
        students = Student.objects.all().select_related('group')
        for student in students:
            writer.writerow([
                student.student_id,
                student.student_fio,
                student.student_birthday,
                student.age(),
                student.get_student_gender_display(),
                student.group.group_name if student.group else '',
                student.student_date_in,
                student.student_date_out or '',
                'Активен' if student.is_active() else 'Выпущен',
            ])
        
        return response
    
    elif report_type == 'attendance_month':
        # Отчет по посещаемости за месяц
        today = date.today()
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
        
        # Данные посещаемости
        attendance = Attendance.objects.filter(
            attendance_date__month=month,
            attendance_date__year=year
        )
        
        present_count = attendance.filter(status=True).count()
        absent_count = attendance.filter(status=False).count()
        total = present_count + absent_count
        
        # Процент посещаемости
        attendance_rate = 0
        if total > 0:
            attendance_rate = round((present_count / total * 100), 2)
        
        month_names = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        
        context = {
            'present_count': present_count,
            'absent_count': absent_count,
            'total': total,
            'attendance_rate': attendance_rate,
            'month': f"{month_names[month-1]} {year}",
            'month_number': month,
            'year': year,
        }
        return render(request, 'kindergarten/report_attendance.html', context)
    
    return redirect('reports')

# ========== ПОИСК ==========
@login_required
def search(request):
    """Поиск по всем данным"""
    query = request.GET.get('q', '')
    if query:
        students = Student.objects.filter(student_fio__icontains=query)
        teachers = Teacher.objects.filter(teacher_fio__icontains=query)
        groups = Group.objects.filter(group_name__icontains=query)
        parents = Parent.objects.filter(parent_fio__icontains=query)
    else:
        students = teachers = groups = parents = []
    
    return render(request, 'kindergarten/search_results.html', {
        'query': query,
        'students': students,
        'teachers': teachers,
        'groups': groups,
        'parents': parents,
    })

# ========== API для статистики ==========
def api_stats(request):
    """API для получения статистики"""
    today = date.today()
    
    stats = {
        'total_students': Student.objects.filter(student_date_out__isnull=True).count(),
        'total_teachers': Teacher.objects.count(),
        'total_groups': Group.objects.count(),
        'total_parents': Parent.objects.count(),
        'attendance_today': Attendance.objects.filter(attendance_date=today, status=True).count(),
        'absent_today': Attendance.objects.filter(attendance_date=today, status=False).count(),
    }
    
    # Распределение по группам
    groups_stats = []
    for group in Group.objects.all():
        groups_stats.append({
            'name': group.group_name,
            'students_count': group.current_students_count(),
            'available': group.available_places(),
            'is_full': group.is_full(),
            'category': group.group_category,
        })
    stats['groups_stats'] = groups_stats
    
    # Посещаемость за последние 7 дней
    attendance_data = []
    attendance_labels = []
    
    for i in range(7):
        day = today - timedelta(days=i)
        present = Attendance.objects.filter(attendance_date=day, status=True).count()
        absent = Attendance.objects.filter(attendance_date=day, status=False).count()
        total = present + absent
        
        attendance_labels.append(day.strftime('%d.%m'))
        if total > 0:
            attendance_data.append(round((present / total) * 100, 1))
        else:
            attendance_data.append(0)
    
    stats['attendance_data'] = list(reversed(attendance_data))
    stats['attendance_labels'] = list(reversed(attendance_labels))
    
    return JsonResponse(stats)