from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()
def user_in_groups(user, group_names):
    return user.groups.filter(name__in=group_names).exists()
def is_director(user):
    return user_in_group(user, 'Заведующие') or user.is_superuser
def is_teacher(user):
    return user_in_group(user, 'Воспитатели')
def is_parent(user):
    return user_in_group(user, 'Родители')
def is_staff_member(user):
    return is_director(user) or is_teacher(user)
def can_manage_users(user):
    return is_director(user)
def can_view_all_groups(user):
    return is_staff_member(user)
def can_edit_group(user, group=None):
    if is_director(user):
        return True
    if is_teacher(user) and group:
        return hasattr(user, 'teacher_profile') and group.teacher == user.teacher_profile
    return False
def can_view_reports(user):
    return is_staff_member(user)
def can_manage_attendance(user, group=None):
    return can_edit_group(user, group)
def get_user_accessible_groups(user):
    from .models import Group
    if is_director(user):
        return Group.objects.all()
    elif is_teacher(user) and hasattr(user, 'teacher_profile'):
        return Group.objects.filter(teacher=user.teacher_profile)
    else:
        return Group.objects.none()
def get_user_accessible_children(user):
    from .models import Child, Student
    if is_director(user):
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
def group_required(*group_names):
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
    return group_required('Заведующие')(view_func)
def staff_required(view_func):
    return group_required('Заведующие', 'Воспитатели')(view_func)
def teacher_or_director_required(view_func):
    return staff_required(view_func)
