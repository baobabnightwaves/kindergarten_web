from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Parent, Teacher, Group as KindergartenGroup
from django.http import HttpResponseForbidden, JsonResponse
def is_superuser(user):
    return user.is_superuser
@login_required
@user_passes_test(is_superuser, login_url='home')
def user_management(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещен")
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    users = User.objects.all().order_by('-date_joined')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    if role_filter:
        users = users.filter(groups__name=role_filter)
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    director_count = User.objects.filter(groups__name='Заведующие').count()
    teacher_count = User.objects.filter(groups__name='Воспитатели').count()
    parent_count = User.objects.filter(groups__name='Родители').count()
    superuser_count = User.objects.filter(is_superuser=True).count()
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    all_groups = Group.objects.filter(name__in=['Родители', 'Воспитатели', 'Заведующие']).order_by('name')
    all_parents = Parent.objects.all().order_by('parent_fio')
    all_teachers = Teacher.objects.all().order_by('teacher_fio')
    context = {
        'users': page_obj,
        'all_groups': all_groups,
        'all_parents': all_parents,
        'all_teachers': all_teachers,
        'director_count': director_count,
        'teacher_count': teacher_count,
        'parent_count': parent_count,
        'superuser_count': superuser_count,
    }
    return render(request, 'kindergarten/users.html', context)
@login_required
@user_passes_test(is_superuser, login_url='home')
def create_user(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещен")
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            full_name = request.POST.get('full_name', '')
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            role = request.POST.get('role', 'parent')
            if email:
                user.email = email
            if role == 'teacher':
                group, _ = Group.objects.get_or_create(name='Воспитатели')
                user.groups.add(group)
                user.is_staff = True
                messages.success(request, f'Воспитатель {full_name} успешно создан!')
            elif role == 'director':
                group, _ = Group.objects.get_or_create(name='Заведующие')
                user.groups.add(group)
                user.is_staff = True
                messages.success(request, f'Заведующий {full_name} успешно создан!')
            elif role == 'superuser':
                user.is_superuser = True
                user.is_staff = True
                messages.success(request, f'Суперпользователь {full_name} успешно создан!')
            else:
                group, _ = Group.objects.get_or_create(name='Родители')
                user.groups.add(group)
                user.is_staff = False
                messages.success(request, f'Родитель {full_name} успешно создан!')
            user.save()
            return redirect('user_management')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register_admin.html', {'form': form})
@login_required
@user_passes_test(is_superuser, login_url='home')
def edit_user(request, user_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещен")
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        try:
            user.email = request.POST.get('email', '')
            user.is_active = 'is_active' in request.POST
            selected_role = request.POST.get('role', None)
            if selected_role == 'superuser':
                user.is_superuser = True
                user.is_staff = True
                user.groups.clear()
                Parent.objects.filter(user=user).update(user=None)
                Teacher.objects.filter(user=user).update(user=None)
            elif selected_role:
                user.is_superuser = False
                user.groups.clear()
                selected_group = Group.objects.get(id=selected_role)
                user.groups.add(selected_group)
                if selected_group.name == 'Родители':
                    user.is_staff = False
                    Teacher.objects.filter(user=user).update(user=None)
                elif selected_group.name in ['Воспитатели', 'Заведующие']:
                    user.is_staff = True
                    Parent.objects.filter(user=user).update(user=None)
            user.save()
            parent_profile_id = request.POST.get('parent_profile', '')
            if parent_profile_id:
                try:
                    old_parent = Parent.objects.filter(user=user).first()
                    if old_parent:
                        old_parent.user = None
                        old_parent.save()
                    new_parent = Parent.objects.get(parent_id=parent_profile_id)
                    if new_parent.user and new_parent.user != user:
                        new_parent.user = None
                        new_parent.save()
                    new_parent.user = user
                    new_parent.save()
                except Parent.DoesNotExist:
                    messages.warning(request, 'Выбранный профиль родителя не найден')
            else:
                old_parent = Parent.objects.filter(user=user).first()
                if old_parent:
                    old_parent.user = None
                    old_parent.save()
            teacher_profile_id = request.POST.get('teacher_profile', '')
            if teacher_profile_id:
                try:
                    old_teacher = Teacher.objects.filter(user=user).first()
                    if old_teacher:
                        old_teacher.user = None
                        old_teacher.save()
                    new_teacher = Teacher.objects.get(teacher_id=teacher_profile_id)
                    if new_teacher.user and new_teacher.user != user:
                        new_teacher.user = None
                        new_teacher.save()
                    new_teacher.user = user
                    new_teacher.save()
                except Teacher.DoesNotExist:
                    messages.warning(request, 'Выбранный профиль воспитателя не найден')
            else:
                old_teacher = Teacher.objects.filter(user=user).first()
                if old_teacher:
                    old_teacher.user = None
                    old_teacher.save()
            messages.success(request, f'Пользователь {user.username} успешно обновлен!')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении: {str(e)}')
    return redirect('user_management')
@login_required
@user_passes_test(is_superuser)
def change_user_password(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        if new_password1 and new_password1 == new_password2:
            user.set_password(new_password1)
            user.save()
            messages.success(request, f'Пароль для {user.username} изменен!')
        else:
            messages.error(request, 'Пароли не совпадают!')
    return redirect('user_management')
@login_required
@user_passes_test(is_superuser)
def activate_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    user.is_active = True
    user.save()
    messages.success(request, f'Пользователь {user.username} активирован!')
    return redirect('user_management')
@login_required
@user_passes_test(is_superuser)
def deactivate_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if user != request.user:
        user.is_active = False
        user.save()
        messages.success(request, f'Пользователь {user.username} деактивирован!')
    else:
        messages.error(request, 'Нельзя деактивировать собственный аккаунт!')
    return redirect('user_management')
@login_required
@user_passes_test(is_superuser)
def delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if user != request.user and not user.is_superuser:
        username = user.username
        user.delete()
        messages.success(request, f'Пользователь {username} удален!')
    else:
        messages.error(request, 'Нельзя удалить этого пользователя!')
    return redirect('user_management')