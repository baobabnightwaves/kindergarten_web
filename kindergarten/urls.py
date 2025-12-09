from django.urls import path
from . import views
from . import views_auth

urlpatterns = [
    # Аутентификация
    path('accounts/login/', views_auth.login_view, name='login'),
    path('accounts/logout/', views_auth.logout_view, name='logout'),
    path('accounts/register/', views_auth.register_view, name='register'),
    path('accounts/profile/', views_auth.profile_view, name='profile'),
    
    # Главная
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    
    # Ученики
    path('students/', views.student_list, name='student_list'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('students/new/', views.student_create, name='student_create'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    
    # Воспитатели
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/<int:pk>/', views.teacher_detail, name='teacher_detail'),
    path('teachers/new/', views.teacher_create, name='teacher_create'),
    path('teachers/<int:pk>/edit/', views.teacher_edit, name='teacher_edit'),
    path('teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),
    
    # Группы
    path('groups/', views.group_list, name='group_list'),
    path('groups/<int:pk>/', views.group_detail, name='group_detail'),
    path('groups/new/', views.group_create, name='group_create'),
    path('groups/<int:pk>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:pk>/delete/', views.group_delete, name='group_delete'),
    
    # Родители
    path('parents/', views.parent_list, name='parent_list'),
    path('parents/<int:pk>/', views.parent_detail, name='parent_detail'),
    path('parents/new/', views.parent_create, name='parent_create'),
    path('parents/<int:pk>/edit/', views.parent_edit, name='parent_edit'),
    path('parents/<int:pk>/delete/', views.parent_delete, name='parent_delete'),
    
    # Связи родитель-ребенок
    path('parents/<int:parent_id>/add-child/', views.add_child_to_parent, name='add_child_to_parent'),
    path('students/<int:student_id>/add-parent/', views.add_parent_to_child, name='add_parent_to_child'),
    path('relations/<int:relation_id>/remove/', views.remove_parent_child_relation, name='remove_parent_child_relation'),
    
    # Посещаемость
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/mark-bulk/', views.attendance_mark_bulk, name='attendance_mark_bulk'),
    path('attendance/update/<int:pk>/', views.attendance_update, name='attendance_update'),
    path('attendance/new/', views.attendance_create, name='attendance_create'),
    path('attendance/<int:pk>/edit/', views.attendance_edit, name='attendance_edit'),
    path('attendance/<int:pk>/delete/', views.attendance_delete, name='attendance_delete'),
    
    # Отчеты
    path('reports/', views.reports, name='reports'),
    path('reports/<str:report_type>/', views.generate_report, name='generate_report'),
    
    # API
    path('api/stats/', views.api_stats, name='api_stats'),
]