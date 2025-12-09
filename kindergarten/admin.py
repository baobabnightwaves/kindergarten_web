from django.contrib import admin
from .models import Student, Teacher, Group, Parent, Attendance, StudentParent, Event

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'student_fio', 'student_birthday', 'group', 'student_date_in')
    list_filter = ('group', 'student_date_in', 'student_gender')
    search_fields = ('student_fio', 'student_address')
    ordering = ('student_fio',)
    date_hierarchy = 'student_date_in'

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('teacher_id', 'teacher_fio', 'teacher_position', 'teacher_number')
    list_filter = ('teacher_position',)
    search_fields = ('teacher_fio', 'teacher_number')

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('group_id', 'group_name', 'group_category', 'group_year', 'teacher', 'room_number')
    list_filter = ('group_category', 'group_year')
    search_fields = ('group_name', 'room_number')

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('parent_id', 'parent_fio', 'parent_number')
    search_fields = ('parent_fio', 'parent_number')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('attendance_id', 'attendance_date', 'student', 'status', 'reason')
    list_filter = ('attendance_date', 'status')
    search_fields = ('student__student_fio', 'reason')
    date_hierarchy = 'attendance_date'

@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = ('student', 'parent', 'relationship_type', 'is_primary')
    list_filter = ('relationship_type', 'is_primary')
    search_fields = ('student__student_fio', 'parent__parent_fio')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_title', 'event_date', 'event_type')
    list_filter = ('event_type', 'event_date')
    date_hierarchy = 'event_date'
    filter_horizontal = ('groups',)