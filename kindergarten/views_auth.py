from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Teacher, Parent
from django.contrib.auth.models import User, Group

def register(request):
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Определяем роль пользователя
            role = request.POST.get('role')
            if role == 'teacher':
                group, created = Group.objects.get_or_create(name='Воспитатели')
                user.groups.add(group)
                
                # Создаем профиль воспитателя
                Teacher.objects.create(
                    user=user,
                    teacher_fio=request.POST.get('full_name', ''),
                    teacher_position='Воспитатель',
                    teacher_number=request.POST.get('phone', '')
                )
                messages.success(request, 'Вы зарегистрированы как воспитатель!')
                
            elif role == 'parent':
                group, created = Group.objects.get_or_create(name='Родители')
                user.groups.add(group)
                
                # Создаем профиль родителя
                Parent.objects.create(
                    user=user,
                    parent_fio=request.POST.get('full_name', ''),
                    parent_number=request.POST.get('phone', '')
                )
                messages.success(request, 'Вы зарегистрированы как родитель!')
            
            elif role == 'director':
                group, created = Group.objects.get_or_create(name='Заведующие')
                user.groups.add(group)
                user.is_staff = True
                user.save()
                messages.success(request, 'Вы зарегистрированы как заведующий!')
            
            # Автоматический вход
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            
            return redirect('home')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def profile(request):
    """Профиль пользователя"""
    user = request.user
    
    # Получаем профиль в зависимости от роли
    profile_data = None
    if hasattr(user, 'teacher_profile'):
        profile_data = user.teacher_profile
        role = 'Воспитатель'
    elif hasattr(user, 'parent_profile'):
        profile_data = user.parent_profile
        role = 'Родитель'
    elif user.groups.filter(name='Заведующие').exists():
        role = 'Заведующий'
    else:
        role = 'Пользователь'
    
    return render(request, 'registration/profile.html', {
        'user': user,
        'profile': profile_data,
        'role': role,
    })