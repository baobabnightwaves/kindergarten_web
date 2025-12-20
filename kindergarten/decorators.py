# kindergarten/decorators.py
from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.shortcuts import redirect

def director_or_superuser_required(view_func):
    """Декоратор для проверки, что пользователь - заведующий или суперпользователь"""
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
    """Декоратор для проверки, что пользователь - воспитатель, заведующий или суперпользователь"""
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