# kindergarten/permissions.py
"""
Centralized permission utilities for the kindergarten application.
This module provides reusable permission checking functions to avoid code duplication.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def user_in_group(user, group_name):
    """
    Check if user belongs to a specific group.
    
    Args:
        user: Django User object
        group_name: Name of the group to check
        
    Returns:
        bool: True if user is in the group, False otherwise
    """
    return user.groups.filter(name=group_name).exists()


def user_in_groups(user, group_names):
    """
    Check if user belongs to any of the specified groups.
    
    Args:
        user: Django User object
        group_names: List of group names to check
        
    Returns:
        bool: True if user is in any of the groups, False otherwise
    """
    return user.groups.filter(name__in=group_names).exists()


def is_director(user):
    """Check if user is a director (Заведующий)"""
    return user_in_group(user, 'Заведующие') or user.is_superuser


def is_teacher(user):
    """Check if user is a teacher (Воспитатель)"""
    return user_in_group(user, 'Воспитатели')


def is_parent(user):
    """Check if user is a parent (Родитель)"""
    return user_in_group(user, 'Родители')


def is_staff_member(user):
    """Check if user is a staff member (director or teacher)"""
    return is_director(user) or is_teacher(user)


def can_manage_users(user):
    """Check if user can manage other users (directors only)"""
    return is_director(user)


def can_view_all_groups(user):
    """Check if user can view all groups (directors and teachers)"""
    return is_staff_member(user)


def can_edit_group(user, group=None):
    """
    Check if user can edit a specific group.
    Directors can edit all groups, teachers can edit only their own groups.
    
    Args:
        user: Django User object
        group: Group object (optional)
        
    Returns:
        bool: True if user can edit the group, False otherwise
    """
    if is_director(user):
        return True
    
    if is_teacher(user) and group:
        # Check if teacher is assigned to this group
        return hasattr(user, 'teacher_profile') and group.teacher == user.teacher_profile
    
    return False


def can_view_reports(user):
    """Check if user can view reports"""
    return is_staff_member(user)


def can_manage_attendance(user, group=None):
    """
    Check if user can manage attendance.
    Directors can manage all, teachers can manage only their groups.
    
    Args:
        user: Django User object
        group: Group object (optional)
        
    Returns:
        bool: True if user can manage attendance, False otherwise
    """
    return can_edit_group(user, group)


def get_user_accessible_groups(user):
    """
    Get all groups accessible to the user.
    
    Args:
        user: Django User object
        
    Returns:
        QuerySet: Groups the user can access
    """
    from .models import Group
    
    if is_director(user):
        return Group.objects.all()
    elif is_teacher(user) and hasattr(user, 'teacher_profile'):
        return Group.objects.filter(teacher=user.teacher_profile)
    else:
        return Group.objects.none()


def get_user_accessible_children(user):
    """
    Get all children accessible to the user.
    
    Args:
        user: Django User object
        
    Returns:
        QuerySet: Children the user can access
    """
    from .models import Child, Student
    
    if is_director(user):
        # Use Student model if Child doesn't exist
        try:
            return Student.objects.all()
        except:
            return Child.objects.all()
    elif is_teacher(user) and hasattr(user, 'teacher_profile'):
        groups = get_user_accessible_groups(user)
        try:
            return Student.objects.filter(group__in=groups)
        except:
            return Child.objects.filter(group__in=groups)
    elif is_parent(user) and hasattr(user, 'parent_profile'):
        parent = user.parent_profile
        try:
            return Student.objects.filter(studentparent__parent=parent)
        except:
            return Child.objects.filter(parent=parent)
    else:
        try:
            return Student.objects.none()
        except:
            return Child.objects.none()


# Decorators for view protection

def group_required(*group_names):
    """
    Decorator to require user to be in one of the specified groups.
    
    Usage:
        @group_required('Заведующие', 'Воспитатели')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Вы должны войти в систему.')
                return redirect('login')
            
            if user_in_groups(request.user, group_names) or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'У вас нет доступа к этой странице.')
                raise PermissionDenied
        
        return wrapper
    return decorator


def director_required(view_func):
    """
    Decorator to require user to be a director.
    
    Usage:
        @director_required
        def my_view(request):
            ...
    """
    return group_required('Заведующие')(view_func)


def staff_required(view_func):
    """
    Decorator to require user to be a staff member (director or teacher).
    
    Usage:
        @staff_required
        def my_view(request):
            ...
    """
    return group_required('Заведующие', 'Воспитатели')(view_func)


def teacher_or_director_required(view_func):
    """Alias for staff_required"""
    return staff_required(view_func)
