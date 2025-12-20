from django.db import models
from django.core.exceptions import ValidationError
from datetime import date
from django.contrib.auth.models import User


class Teacher(models.Model):
    POSITION_CHOICES = [
        ('Младший воспитатель', 'Младший воспитатель'),
        ('Воспитатель', 'Воспитатель'),
        ('Старший воспитатель', 'Старший воспитатель'),
        ('Заведующий', 'Заведующий'),
        ('Методист', 'Методист'),
    ]
    
    teacher_id = models.AutoField(primary_key=True)
    teacher_fio = models.CharField(max_length=100, verbose_name='ФИО воспитателя', db_index=True)
    teacher_position = models.CharField(max_length=50, choices=POSITION_CHOICES, 
                                       default='Воспитатель', verbose_name='Должность', db_index=True)
    teacher_number = models.CharField(max_length=20, verbose_name='Номер телефона')
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, 
                               related_name='teacher_profile')
    
    def __str__(self):
        return f"{self.teacher_fio} ({self.teacher_position})"
    
    class Meta:
        verbose_name = 'Воспитатель'
        verbose_name_plural = 'Воспитатели'
        indexes = [
            models.Index(fields=['teacher_fio', 'teacher_position']),
        ]

class Group(models.Model):
    CATEGORY_CHOICES = [
        ('Младшая', 'Младшая (2-3 года)'),
        ('Средняя', 'Средняя (3-4 года)'),
        ('Старшая', 'Старшая (4-5 лет)'),
        ('Подготовительная', 'Подготовительная (5-7 лет)'),
    ]
    
    MAX_STUDENTS = 30  # Максимальная наполняемость группы
    
    group_id = models.AutoField(primary_key=True)
    group_name = models.CharField(max_length=50, unique=True, verbose_name='Название группы', db_index=True)
    group_category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, 
                                     verbose_name='Возрастная категория', db_index=True)
    group_year = models.IntegerField(verbose_name='Год обучения', default=2024, db_index=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, 
                               blank=True, verbose_name='Воспитатель')
    room_number = models.CharField(max_length=10, verbose_name='Номер кабинета', 
                                  default='101')
    max_capacity = models.IntegerField(verbose_name='Максимальная наполняемость', 
                                      default=MAX_STUDENTS)
    
    def current_students_count(self):
        """Optimized to use cached count if available"""
        return self.student_set.count()
    
    def available_places(self):
        return self.max_capacity - self.current_students_count()
    
    def is_full(self):
        return self.current_students_count() >= self.max_capacity
    
    def clean(self):
        if self.current_students_count() > self.max_capacity:
            raise ValidationError(f'Группа не может содержать более {self.max_capacity} учеников')
    
    def __str__(self):
        return f"{self.group_name} ({self.group_category})"
    
    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
        indexes = [
            models.Index(fields=['group_category', 'group_year']),
            models.Index(fields=['teacher', 'group_year']),
        ]

class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    student_fio = models.CharField(max_length=100, verbose_name='ФИО ученика', db_index=True)
    student_birthday = models.DateField(verbose_name='Дата рождения', db_index=True)
    student_gender = models.CharField(max_length=1, choices=[('М', 'Мужской'), ('Ж', 'Женский')], 
                                     verbose_name='Пол')
    student_address = models.TextField(verbose_name='Адрес проживания', blank=True)
    student_date_in = models.DateField(verbose_name='Дата поступления', db_index=True)
    student_date_out = models.DateField(verbose_name='Дата выпуска', null=True, blank=True, db_index=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, 
                             verbose_name='Группа')
    
    def age(self):
        today = date.today()
        born = self.student_birthday
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    
    def is_active(self):
        """Check if student is currently active"""
        return self.student_date_out is None or self.student_date_out > date.today()
    
    def clean(self):    
        age_at_entry = self.age_at_entry()
        if age_at_entry < 2 or age_at_entry > 7:
            raise ValidationError('Прием детей в детский сад осуществляется только в возрасте от 2 до 7 лет')
        if self.group and self.group.is_full() and not self.pk:
            raise ValidationError(f'Группа "{self.group.group_name}" уже заполнена (максимум {self.group.max_capacity} учеников)')
    
    def age_at_entry(self):
        if self.student_date_in and self.student_birthday:
            entry_date = self.student_date_in
            born = self.student_birthday
            return entry_date.year - born.year - ((entry_date.month, entry_date.day) < (born.month, born.day))
        return 0
    
    def __str__(self):
        status = "Активен" if self.is_active() else "Выпущен"
        return f"{self.student_fio} ({self.age()} лет, {status})"
    
    class Meta:
        verbose_name = 'Ученик'
        verbose_name_plural = 'Ученики'
        indexes = [
            models.Index(fields=['group', 'student_date_out']),  # For active students in group
            models.Index(fields=['student_fio', 'student_birthday']),  # For search queries
        ]

class Parent(models.Model):
    RELATIONSHIP_CHOICES = [
        ('Мать', 'Мать'),
        ('Отец', 'Отец'),
        ('Бабушка', 'Бабушка'),
        ('Дедушка', 'Дедушка'),
        ('Опекун', 'Опекун'),
        ('Другое', 'Другое'),
    ]
    
    parent_id = models.AutoField(primary_key=True)
    parent_fio = models.CharField(max_length=100, verbose_name='ФИО родителя', db_index=True)
    parent_number = models.CharField(max_length=20, verbose_name='Номер телефона', db_index=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, 
                               related_name='parent_profile')
    
    def __str__(self):
        return self.parent_fio
    
    class Meta:
        verbose_name = 'Родитель'
        verbose_name_plural = 'Родители'
        indexes = [
            models.Index(fields=['parent_fio', 'parent_number']),
        ]

class StudentParent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='Ученик')
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, verbose_name='Родитель')
    relationship_type = models.CharField(max_length=20, choices=Parent.RELATIONSHIP_CHOICES, 
                                        verbose_name='Степень родства')
    is_primary = models.BooleanField(default=True, verbose_name='Основной контакт')
    
    def __str__(self):
        return f"{self.parent.parent_fio} - {self.relationship_type} - {self.student.student_fio}"
    
    class Meta:
        verbose_name = 'Связь ученик-родитель'
        verbose_name_plural = 'Связи ученик-родитель'
        unique_together = ('student', 'parent')

class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    attendance_date = models.DateField(verbose_name='Дата посещения', db_index=True)
    status = models.BooleanField(verbose_name='Статус', choices=[(True, 'Присутствовал'), (False, 'Отсутствовал')], db_index=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='Ученик')
    reason = models.CharField(max_length=100, verbose_name='Причина отсутствия', blank=True, 
                             choices=[
                                 ('', 'Не указана'),
                                 ('Болезнь', 'Болезнь'),
                                 ('Отпуск', 'Отпуск родителей'),
                                 ('Семейные обстоятельства', 'Семейные обстоятельства'),
                                 ('Другое', 'Другое'),
                             ])
    noted_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, 
                                verbose_name='Отметил воспитатель')
    
    def __str__(self):
        status_text = "Присутствовал" if self.status else "Отсутствовал"
        return f"{self.student.student_fio} - {self.attendance_date} - {status_text}"
    
    class Meta:
        verbose_name = 'Посещаемость'
        verbose_name_plural = 'Посещаемость'
        unique_together = ('attendance_date', 'student')  # Одна запись на день для ученика
        indexes = [
            models.Index(fields=['student', 'attendance_date']),  # For student attendance history
            models.Index(fields=['attendance_date', 'status']),  # For daily reports
            models.Index(fields=['student', 'status', 'attendance_date']),  # For student status queries
        ]

class Event(models.Model):
    EVENT_TYPES = [
        ('holiday', 'Праздник'),
        ('meeting', 'Родительское собрание'),
        ('excursion', 'Экскурсия'),
        ('medical', 'Медосмотр'),
        ('other', 'Другое'),
    ]
    
    event_id = models.AutoField(primary_key=True)
    event_title = models.CharField(max_length=200, verbose_name='Название события')
    event_description = models.TextField(verbose_name='Описание', blank=True)
    event_date = models.DateField(verbose_name='Дата события')
    event_time = models.TimeField(verbose_name='Время', blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='other', 
                                 verbose_name='Тип события')
    groups = models.ManyToManyField(Group, blank=True, verbose_name='Группы')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.event_title} - {self.event_date}"
    
    class Meta:
        verbose_name = 'Событие'
        verbose_name_plural = 'События'
        ordering = ['event_date']