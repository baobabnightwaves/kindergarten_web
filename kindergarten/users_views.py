# Создайте новый файл users_views.py или добавьте в views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Parent, Teacher
from django.http import HttpResponseForbidden, JsonResponse


def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser, login_url='home')
def user_management(request):
    """Управление пользователями"""
    if not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещен")
    
    # Фильтрация
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # Начинаем с всех пользователей
    users = User.objects.all().order_by('-date_joined')
    
    # Применяем фильтры
    if search_query:
        # TODO: Поиск по parent_profile/teacher_profile отключен (нет связи в БД)
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
    
    # Статистика
    director_count = User.objects.filter(groups__name='Заведующие').count()
    teacher_count = User.objects.filter(groups__name='Воспитатели').count()
    parent_count = User.objects.filter(groups__name='Родители').count()
    superuser_count = User.objects.filter(is_superuser=True).count()
    
    # Пагинация
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    all_groups = Group.objects.all()
    
    context = {
        'users': page_obj,
        'all_groups': all_groups,
        'director_count': director_count,
        'teacher_count': teacher_count,
        'parent_count': parent_count,
        'superuser_count': superuser_count,
    }
    
    return render(request, 'kindergarten/users.html', context)

@login_required
@user_passes_test(is_superuser, login_url='home')
def create_user(request):
    """Создание нового пользователя с выбором роли"""
    if not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещен")
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            
            # Получаем данные из формы
            full_name = request.POST.get('full_name', '')
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            role = request.POST.get('role', 'parent')
            
            # Устанавливаем email
            if email:
                user.email = email
            
            # Назначаем роль
            if role == 'teacher':
                group, _ = Group.objects.get_or_create(name='Воспитатели')
                user.groups.add(group)
                user.is_staff = True  # Воспитатель - персонал
                user.save()
                
                # TODO: Создание профиля воспитателя отключено (нет связи в БД)
                pass
                messages.success(request, f'Воспитатель {full_name} успешно создан!')
                
            elif role == 'director':
                group, _ = Group.objects.get_or_create(name='Заведующие')
                user.groups.add(group)
                user.is_staff = True  # Заведующий - персонал
                user.save()
                
                # TODO: Создание профиля заведующего отключено (нет связи в БД)
                pass
                messages.success(request, f'Заведующий {full_name} успешно создан!')
                
            elif role == 'superuser':
                # Делаем пользователя суперпользователем
                user.is_superuser = True
                user.is_staff = True
                user.save()
                messages.success(request, f'Суперпользователь {full_name} успешно создан!')
                
            else:  # parent (по умолчанию)
                group, _ = Group.objects.get_or_create(name='Родители')
                user.groups.add(group)
                user.is_staff = False  # Родитель НЕ персонал
                user.save()
                
                # TODO: Создание профиля родителя отключено (нет связи в БД)
                pass
                messages.success(request, f'Родитель {full_name} успешно создан!')
            
            return redirect('user_management')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register_admin.html', {'form': form})

@login_required
@user_passes_test(is_superuser, login_url='home')
def edit_user(request, user_id):
    """Редактирование пользователя с проверкой конфликтов ролей"""
    if not request.user.is_superuser:
        return HttpResponseForbidden("Доступ запрещен")
    
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        try:
            # Обновляем основные поля
            user.email = request.POST.get('email', '')
            user.is_active = 'is_active' in request.POST
            
            # Получаем выбранные группы
            selected_groups = request.POST.getlist('groups', [])
            
            # Проверяем конфликты ролей
            groups = Group.objects.filter(id__in=selected_groups)
            
            # Нельзя быть одновременно родителем и воспитателем/заведующим
            if groups.filter(name='Родители').exists() and groups.filter(name__in=['Воспитатели', 'Заведующие']).exists():
                messages.error(request, 'Пользователь не может быть одновременно родителем и воспитателем/заведующим!')
                return redirect('user_management')
            
            # Нельзя быть одновременно воспитателем и заведующим
            if groups.filter(name='Воспитатели').exists() and groups.filter(name='Заведующие').exists():
                messages.error(request, 'Пользователь не может быть одновременно воспитателем и заведующим!')
                return redirect('user_management')
            
            # Обновляем группы
            user.groups.clear()
            for group in groups:
                user.groups.add(group)
            
            # Обновляем статус персонала
            # Родители НЕ могут быть персоналом
            if groups.filter(name='Родители').exists():
                user.is_staff = False
            else:
                user.is_staff = 'is_staff' in request.POST
            
            # Суперпользователь всегда персонал
            if user.is_superuser:
                user.is_staff = True
            
            user.save()
            
            # Обновляем профиль
            full_name = request.POST.get('full_name', '')
            phone = request.POST.get('phone', '')
            
            # TODO: Управление профилями отключено (нет связи user-teacher/parent в БД)
            # Старая логика удаления профилей закомментирована
            
            # TODO: Создание профилей отключено (нет связи user-teacher/parent в БД)
            # Старая логика создания профилей закомментирована
            
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
    if user != request.user:  # Нельзя деактивировать самого себя
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
    if user != request.user and not user.is_superuser:  # Нельзя удалить себя или суперпользователя
        username = user.username
        user.delete()
        messages.success(request, f'Пользователь {username} удален!')
    else:
        messages.error(request, 'Нельзя удалить этого пользователя!')
    return redirect('user_management')