from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User, Group
from .models import Teacher, Parent
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})
def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('home')
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        user_form = UserCreationForm(request.POST)
        if user_form.is_valid():
            user = user_form.save()            
            role = request.POST.get('role', 'parent')
            if role == 'teacher':
                group, _ = Group.objects.get_or_create(name='Воспитатели')
                user.groups.add(group)                
                Teacher.objects.create(
                    user=user,
                    teacher_fio=request.POST.get('full_name', ''),
                    teacher_position='Воспитатель',
                    teacher_number=request.POST.get('phone', '')
                )
                messages.success(request, 'Вы зарегистрированы как воспитатель!')
            elif role == 'director':
                group, _ = Group.objects.get_or_create(name='Заведующие')
                user.groups.add(group)
                user.is_staff = True
                user.save()
                messages.success(request, 'Вы зарегистрированы как заведующий!')
            else:
                group, _ = Group.objects.get_or_create(name='Родители')
                user.groups.add(group)
                Parent.objects.create(
                    user=user,
                    parent_fio=request.POST.get('full_name', ''),
                    parent_number=request.POST.get('phone', '')
                )
                messages.success(request, 'Вы зарегистрированы как родитель!')
            login(request, user)
            return redirect('home')
    else:
        user_form = UserCreationForm()
    return render(request, 'registration/register_admin.html', {'form': user_form})
@login_required
def profile_view(request):
    user = request.user
    profile = None
    role = 'Пользователь'
    if user.groups.filter(name='Воспитатели').exists():
        role = 'Воспитатель'
        if hasattr(user, 'teacher_profile'):
            profile = user.teacher_profile
    elif user.groups.filter(name='Заведующие').exists():
        role = 'Заведующий'
    elif user.groups.filter(name='Родители').exists():
        role = 'Родитель'
        if hasattr(user, 'parent_profile'):
            profile = user.parent_profile
    return render(request, 'registration/profile.html', {
        'user': user,
        'profile': profile,
        'role': role
    })
def is_teacher(user):
    return user.groups.filter(name='Воспитатели').exists() or user.is_superuser
def is_director(user):
    return user.groups.filter(name='Заведующие').exists() or user.is_superuser
def is_parent(user):
    return user.groups.filter(name='Родители').exists() or user.is_superuser
def is_admin(user):
    return user.is_superuser or user.is_staff
@login_required
@user_passes_test(is_director, login_url='login')
def admin_dashboard(request):
    return render(request, 'dashboard/admin_dashboard.html')
