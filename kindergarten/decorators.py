from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.shortcuts import redirect
def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'superuser'
    elif user.groups.filter(name='Заведующие').exists():
        return 'director'
    elif user.groups.filter(name='Воспитатели').exists():
        return 'teacher'
    elif user.groups.filter(name='Родители').exists():
        return 'parent'
    return None
def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            user_role = get_user_role(request.user)
            if user_role == 'superuser':
                return view_func(request, *args, **kwargs)
            if user_role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'У вас нет прав для выполнения этого действия!')
            return redirect('home')
        return _wrapped_view
    return decorator
def director_or_superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser or request.user.groups.filter(name='Заведующие').exists():
            return view_func(request, *args, **kwargs)
        messages.error(request, 'У вас нет прав для выполнения этого действия!')
        return redirect('home')
    return _wrapped_view
def teacher_director_or_superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if (request.user.is_superuser or 
            request.user.groups.filter(name='Заведующие').exists() or
            request.user.groups.filter(name='Воспитатели').exists()):
            return view_func(request, *args, **kwargs)
        messages.error(request, 'У вас нет прав для выполнения этого действия!')
        return redirect('home')
    return _wrapped_view
def parent_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser or request.user.groups.filter(name='Родители').exists():
            return view_func(request, *args, **kwargs)
        messages.error(request, 'У вас нет прав для выполнения этого действия!')
        return redirect('home')
    return _wrapped_view