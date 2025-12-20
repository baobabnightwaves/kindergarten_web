#!/usr/bin/env python
"""
Скрипт для заполнения базы данных тестовыми данными
Запуск: python manage.py shell < fill.py
Или: python manage.py shell, затем выполнить команды вручную
"""

import os
import sys
import random
from datetime import datetime, date, timedelta

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kindergarten_web.settings')

import django
django.setup()

from django.contrib.auth.models import User, Group
from kindergarten.models import Student, Teacher, Group as KindergartenGroup, Parent, Attendance, StudentParent, Event
from django.utils import timezone

def print_separator():
    print("=" * 60)

def create_superuser():
    """Создать суперпользователя"""
    print("Создание суперпользователя...")
    
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@kindergarten.ru',
            first_name='Администратор',
            last_name='Системы'
        )
        print("✅ Суперпользователь создан: admin / admin123")
    else:
        print("ℹ️ Суперпользователь уже существует")

def create_groups():
    """Создать тестовые группы"""
    print("\nСоздание групп...")
    
    groups_data = [
        {'name': 'Солнышко', 'category': 'Младшая', 'room': '101'},
        {'name': 'Звездочка', 'category': 'Средняя', 'room': '102'},
        {'name': 'Радуга', 'category': 'Старшая', 'room': '201'},
        {'name': 'Умка', 'category': 'Подготовительная', 'room': '202'},
    ]
    
    groups = []
    for data in groups_data:
        group, created = KindergartenGroup.objects.get_or_create(
            group_name=data['name'],
            defaults={
                'group_category': data['category'],
                'group_year': 2024,
                'room_number': data['room'],
                'max_capacity': 15
            }
        )
        if created:
            groups.append(group)
            print(f"✅ Создана группа: {group.group_name}")
        else:
            print(f"ℹ️ Группа уже существует: {group.group_name}")
    
    return groups

def create_teachers():
    """Создать тестовых воспитателей"""
    print("\nСоздание воспитателей...")
    
    teachers_data = [
        {'fio': 'Иванова Мария Петровна', 'position': 'Воспитатель', 'phone': '+7-916-123-45-67'},
        {'fio': 'Петрова Анна Сергеевна', 'position': 'Воспитатель', 'phone': '+7-925-234-56-78'},
        {'fio': 'Сидорова Ольга Ивановна', 'position': 'Старший воспитатель', 'phone': '+7-903-345-67-89'},
        {'fio': 'Кузнецова Елена Владимировна', 'position': 'Воспитатель', 'phone': '+7-916-456-78-90'},
    ]
    
    teachers = []
    for i, data in enumerate(teachers_data):
        username = f'teacher{i+1}'
        
        # Создаем пользователя
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@kindergarten.ru',
                'password': 'teacher123'
            }
        )
        
        if created:
            user.set_password('teacher123')
            user.save()
            
            # Добавляем в группу воспитателей
            teacher_group, _ = Group.objects.get_or_create(name='Воспитатели')
            user.groups.add(teacher_group)
        
        # Создаем или получаем профиль воспитателя
        teacher, created = Teacher.objects.get_or_create(
            user=user,
            defaults={
                'teacher_fio': data['fio'],
                'teacher_position': data['position'],
                'teacher_number': data['phone']
            }
        )
        
        if created:
            teachers.append(teacher)
            print(f"✅ Создан воспитатель: {teacher.teacher_fio}")
        else:
            print(f"ℹ️ Воспитатель уже существует: {teacher.teacher_fio}")
    
    return teachers

def create_directors():
    """Создать заведующих"""
    print("\nСоздание заведующих...")
    
    directors_data = [
        {'username': 'director', 'fio': 'Семенова Галина Ивановна', 'phone': '+7-916-111-22-33'},
    ]
    
    directors = []
    for data in directors_data:
        # Создаем пользователя
        user, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'email': f'{data["username"]}@kindergarten.ru',
                'password': 'director123',
                'is_staff': True
            }
        )
        
        if created:
            user.set_password('director123')
            user.save()
            
            # Добавляем в группу заведующих
            director_group, _ = Group.objects.get_or_create(name='Заведующие')
            user.groups.add(director_group)
        
        # Создаем профиль воспитателя для заведующего
        director, created = Teacher.objects.get_or_create(
            user=user,
            defaults={
                'teacher_fio': data['fio'],
                'teacher_position': 'Заведующий',
                'teacher_number': data['phone']
            }
        )
        
        if created:
            directors.append(director)
            print(f"✅ Создан заведующий: {director.teacher_fio}")
        else:
            print(f"ℹ️ Заведующий уже существует: {director.teacher_fio}")
    
    return directors

def create_parents():
    """Создать родителей"""
    print("\nСоздание родителей...")
    
    parents_data = [
        {'username': 'parent1', 'fio': 'Иванов Иван Иванович', 'phone': '+7-916-222-33-44'},
        {'username': 'parent2', 'fio': 'Петров Петр Петрович', 'phone': '+7-916-333-44-55'},
        {'username': 'parent3', 'fio': 'Сидорова Анна Сергеевна', 'phone': '+7-916-444-55-66'},
        {'username': 'parent4', 'fio': 'Кузнецова Мария Алексеевна', 'phone': '+7-916-555-66-77'},
        {'username': 'parent5', 'fio': 'Смирнов Дмитрий Викторович', 'phone': '+7-916-666-77-88'},
    ]
    
    parents = []
    for data in parents_data:
        user, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'email': f'{data["username"]}@example.com',
                'password': 'parent123'
            }
        )
        
        if created:
            user.set_password('parent123')
            user.save()
            
            # Добавляем в группу родителей
            parent_group, _ = Group.objects.get_or_create(name='Родители')
            user.groups.add(parent_group)
        
        # Создаем профиль родителя
        parent, created = Parent.objects.get_or_create(
            user=user,
            defaults={
                'parent_fio': data['fio'],
                'parent_number': data['phone']
            }
        )
        
        if created:
            parents.append(parent)
            print(f"✅ Создан родитель: {parent.parent_fio}")
        else:
            print(f"ℹ️ Родитель уже существует: {parent.parent_fio}")
    
    return parents

def create_students(groups, parents):
    """Создать учеников"""
    print("\nСоздание учеников...")
    
    students_data = [
        {'fio': 'Иванов Артем Иванович', 'gender': 'М', 'group_idx': 0, 'parent_idx': [0]},
        {'fio': 'Петров Максим Петрович', 'gender': 'М', 'group_idx': 0, 'parent_idx': [1]},
        {'fio': 'Сидорова София Сергеевна', 'gender': 'Ж', 'group_idx': 1, 'parent_idx': [2]},
        {'fio': 'Кузнецов Даниил Алексеевич', 'gender': 'М', 'group_idx': 1, 'parent_idx': [3]},
        {'fio': 'Смирнова Полина Дмитриевна', 'gender': 'Ж', 'group_idx': 2, 'parent_idx': [4]},
        {'fio': 'Иванова Анастасия Ивановна', 'gender': 'Ж', 'group_idx': 2, 'parent_idx': [0]},
        {'fio': 'Петрова Екатерина Петровна', 'gender': 'Ж', 'group_idx': 3, 'parent_idx': [1]},
        {'fio': 'Сидоров Кирилл Сергеевич', 'gender': 'М', 'group_idx': 3, 'parent_idx': [2]},
    ]
    
    students = []
    today = date.today()
    
    for data in students_data:
        # Генерируем даты
        age = random.randint(3, 6)
        birthday = date(today.year - age, random.randint(1, 12), random.randint(1, 28))
        date_in = date(birthday.year + 2, random.randint(1, 12), random.randint(1, 28))
        
        # Выбираем группу
        group = groups[data['group_idx'] % len(groups)]
        
        # Создаем ученика
        student, created = Student.objects.get_or_create(
            student_fio=data['fio'],
            defaults={
                'student_birthday': birthday,
                'student_gender': data['gender'],
                'student_address': f'г. Москва, ул. {random.choice(["Ленина", "Пушкина", "Гагарина"])}, д. {random.randint(1, 50)}',
                'student_date_in': date_in,
                'group': group
            }
        )
        
        if created:
            students.append(student)
            print(f"✅ Создан ученик: {student.student_fio} (Группа: {group.group_name})")
            
            # Создаем связи с родителями
            for parent_idx in data['parent_idx']:
                if parent_idx < len(parents):
                    StudentParent.objects.get_or_create(
                        student=student,
                        parent=parents[parent_idx],
                        defaults={
                            'relationship_type': random.choice(['Мать', 'Отец']),
                            'is_primary': True
                        }
                    )
        else:
            print(f"ℹ️ Ученик уже существует: {data['fio']}")
    
    return students

def assign_teachers_to_groups(groups, teachers):
    """Назначить воспитателей группам"""
    print("\nНазначение воспитателей группам...")
    
    for i, group in enumerate(groups):
        if i < len(teachers):
            group.teacher = teachers[i]
            group.save()
            print(f"✅ Воспитатель {teachers[i].teacher_fio} назначен в группу {group.group_name}")

def create_attendance(students):
    """Создать записи о посещаемости"""
    print("\nСоздание записей о посещаемости...")
    
    today = date.today()
    teachers = Teacher.objects.filter(teacher_position='Воспитатель')
    count = 0
    
    # Создаем посещаемость за последние 7 дней
    for i in range(7):
        attendance_date = today - timedelta(days=i)
        
        # Пропускаем выходные
        if attendance_date.weekday() >= 5:
            continue
        
        for student in students:
            # 80% присутствуют, 20% отсутствуют
            status = random.random() < 0.8
            
            if not status:
                reasons = ['Болезнь', 'Отпуск', 'Семейные обстоятельства']
                reason = random.choice(reasons)
            else:
                reason = ''
            
            Attendance.objects.get_or_create(
                attendance_date=attendance_date,
                student=student,
                defaults={
                    'status': status,
                    'reason': reason,
                    'noted_by': random.choice(list(teachers)) if teachers.exists() else None
                }
            )
            count += 1
    
    print(f"✅ Создано {count} записей о посещаемости")
    return count

def create_events(groups):
    """Создать события"""
    print("\nСоздание событий...")
    
    events_data = [
        {'title': 'Новогодний утренник', 'type': 'holiday', 'date_offset': 10},
        {'title': 'Родительское собрание', 'type': 'meeting', 'date_offset': 5},
        {'title': 'Экскурсия в музей', 'type': 'excursion', 'date_offset': 15},
        {'title': 'Медосмотр', 'type': 'medical', 'date_offset': 8},
    ]
    
    today = date.today()
    
    for data in events_data:
        event_date = today + timedelta(days=data['date_offset'])
        event_time = datetime.strptime(f"{random.randint(10, 16)}:00", "%H:%M").time()
        
        event, created = Event.objects.get_or_create(
            event_title=data['title'],
            event_date=event_date,
            defaults={
                'event_description': f'Описание мероприятия "{data["title"]}"',
                'event_time': event_time,
                'event_type': data['type'],
                'created_at': timezone.now()
            }
        )
        
        if created:
            # Добавляем все группы к событию
            event.groups.set(groups)
            print(f"✅ Создано событие: {event.event_title} ({event.event_date})")
        else:
            print(f"ℹ️ Событие уже существует: {data['title']}")

def print_statistics():
    """Вывести статистику"""
    print_separator()
    print("СТАТИСТИКА БАЗЫ ДАННЫХ")
    print_separator()
    print(f"Группы: {KindergartenGroup.objects.count()}")
    print(f"Воспитатели: {Teacher.objects.count()}")
    print(f"Родители: {Parent.objects.count()}")
    print(f"Ученики: {Student.objects.count()}")
    print(f"Связи ученик-родитель: {StudentParent.objects.count()}")
    print(f"Посещаемость: {Attendance.objects.count()}")
    print(f"События: {Event.objects.count()}")
    print_separator()
    
    print("\n👤 ТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ:")
    print("=" * 30)
    print("Суперпользователь:")
    print("  Логин: admin")
    print("  Пароль: admin123")
    print("  Роль: Полный доступ ко всему")
    print("\nЗаведующий (администратор сада):")
    print("  Логин: director")
    print("  Пароль: director123")
    print("  Роль: Все кроме управления пользователями")
    print("\nВоспитатели:")
    print("  Логины: teacher1, teacher2, teacher3, teacher4")
    print("  Пароль: teacher123")
    print("  Роль: Посещаемость, отчеты, их группы")
    print("\nРодители:")
    print("  Логины: parent1, parent2, parent3, parent4, parent5")
    print("  Пароль: parent123")
    print("  Роль: Просмотр информации о своем ребенке")
    print_separator()

def main():
    """Основная функция"""
    print_separator()
    print("🚀 НАЧАЛО ЗАПОЛНЕНИЯ БАЗЫ ДАННЫХ")
    print_separator()
    
    try:
        # Создаем суперпользователя
        create_superuser()
        
        # Создаем группы
        groups = create_groups()
        
        # Создаем воспитателей
        teachers = create_teachers()
        
        # Создаем заведующих
        directors = create_directors()
        
        # Создаем родителей
        parents = create_parents()
        
        # Создаем учеников
        students = create_students(groups, parents)
        
        # Назначаем воспитателей группам
        assign_teachers_to_groups(groups, teachers)
        
        # Создаем посещаемость
        create_attendance(students)
        
        # Создаем события
        create_events(groups)
        
        # Выводим статистику
        print_statistics()
        
        print("🎉 БАЗА ДАННЫХ УСПЕШНО ЗАПОЛНЕНА!")
        print("Перейдите по адресу http://127.0.0.1:8000/ для начала работы")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()