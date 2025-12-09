from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import Student, Teacher, Group, Parent, Attendance, StudentParent, Event

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'
        widgets = {
            'student_birthday': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'student_date_in': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'student_date_out': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'student_fio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
            'student_gender': forms.Select(attrs={'class': 'form-control'}),
            'student_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'г. Москва, ул. Ленина, д. 1'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        student_birthday = cleaned_data.get('student_birthday')
        student_date_in = cleaned_data.get('student_date_in')
        group = cleaned_data.get('group')
        
        # Проверка возраста (2-7 лет при поступлении)
        if student_birthday and student_date_in:
            age_at_entry = student_date_in.year - student_birthday.year - (
                (student_date_in.month, student_date_in.day) < (student_birthday.month, student_birthday.day)
            )
            if age_at_entry < 2 or age_at_entry > 7:
                raise ValidationError('Прием детей в детский сад осуществляется только в возрасте от 2 до 7 лет')
        
        # Проверка заполненности группы
        if group and group.is_full() and not self.instance.pk:
            raise ValidationError(f'Группа "{group.group_name}" уже заполнена (максимум {group.max_capacity} учеников)')
        
        return cleaned_data

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = '__all__'
        widgets = {
            'teacher_fio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванова Мария Петровна'}),
            'teacher_position': forms.Select(attrs={'class': 'form-control'}),
            'teacher_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7-999-123-45-67'}),
        }

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = '__all__'
        widgets = {
            'group_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Солнышко'}),
            'group_category': forms.Select(attrs={'class': 'form-control'}),
            'group_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '2020', 'max': '2030'}),
            'teacher': forms.Select(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '101'}),
            'max_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '30', 'value': '30'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        max_capacity = cleaned_data.get('max_capacity')
        
        # Проверка максимальной наполняемости
        if max_capacity and max_capacity > 30:
            raise ValidationError('Группа не может содержать более 30 учеников')
        
        return cleaned_data

class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = '__all__'
        widgets = {
            'parent_fio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванова Анна Сергеевна'}),
            'parent_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7-999-123-45-67'}),
        }

class StudentParentForm(forms.ModelForm):
    class Meta:
        model = StudentParent
        fields = '__all__'
        widgets = {
            'relationship_type': forms.Select(attrs={'class': 'form-control'}),
            'student': forms.Select(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = '__all__'
        widgets = {
            'attendance_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(choices=[(True, 'Присутствовал'), (False, 'Отсутствовал')], 
                                  attrs={'class': 'form-control'}),
            'student': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'noted_by': forms.Select(attrs={'class': 'form-control'}),
        }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = '__all__'
        widgets = {
            'event_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'event_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'event_title': forms.TextInput(attrs={'class': 'form-control'}),
            'event_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'event_type': forms.Select(attrs={'class': 'form-control'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

class AddChildToParentForm(forms.Form):
    parent = forms.ModelChoiceField(
        queryset=Parent.objects.all(),
        label='Родитель',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        label='Ребенок',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    relationship_type = forms.ChoiceField(
        choices=Parent.RELATIONSHIP_CHOICES,
        label='Степень родства',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_primary = forms.BooleanField(
        label='Основной контакт',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class AddParentToChildForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        label='Ребенок',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    parent = forms.ModelChoiceField(
        queryset=Parent.objects.all(),
        label='Родитель',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    relationship_type = forms.ChoiceField(
        choices=Parent.RELATIONSHIP_CHOICES,
        label='Степень родства',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_primary = forms.BooleanField(
        label='Основной контакт',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )