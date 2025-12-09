import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kindergarten_web.settings')
django.setup()

from django.contrib.auth.models import User
from kindergarten.models import Teacher, Group, Student, Parent, StudentParent, Attendance

print("🎲 Заполняем базу тестовыми данными...")

# 1. Суперпользователь
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ Создан администратор")

# 2. Воспитатели
if Teacher.objects.count() == 0:
    teacher1 = Teacher.objects.create(
        teacher_fio='Иванова Мария Петровна',
        teacher_position='Старший воспитатель',
        teacher_number='+7-999-123-45-67'
    )
    teacher2 = Teacher.objects.create(
        teacher_fio='Петрова Анна Сергеевна',
        teacher_position='Воспитатель',
        teacher_number='+7-999-123-45-68'
    )
    print("✅ Созданы воспитатели")

# 3. Группы
if Group.objects.count() == 0:
    teachers = Teacher.objects.all()
    
    group1 = Group.objects.create(
        group_name='Солнышко',
        group_category='Младшая',
        group_year=2024,
        teacher=teachers[0],
        room_number='101'
    )
    group2 = Group.objects.create(
        group_name='Ромашка',
        group_category='Средняя',
        group_year=2024,
        teacher=teachers[1] if len(teachers) > 1 else teachers[0],
        room_number='102'
    )
    group3 = Group.objects.create(
        group_name='Звездочка',
        group_category='Старшая',
        group_year=2024,
        teacher=teachers[0],
        room_number='103'
    )
    print("✅ Созданы группы")

# 4. Ученики
if Student.objects.count() == 0:
    groups = Group.objects.all()
    
    students = [
        Student(
            student_fio='Смирнов Александр Иванович',
            student_birthday=date(2020, 5, 15),
            student_gender='М',
            student_address='г. Москва, ул. Ленина, д. 1',
            student_date_in=date(2023, 9, 1),
            group=groups[0]
        ),
        Student(
            student_fio='Кузнецова София Андреевна',
            student_birthday=date(2019, 8, 22),
            student_gender='Ж',
            student_address='г. Москва, ул. Пушкина, д. 10',
            student_date_in=date(2022, 9, 1),
            group=groups[1] if len(groups) > 1 else groups[0]
        ),
        Student(
            student_fio='Попов Максим Сергеевич',
            student_birthday=date(2018, 3, 10),
            student_gender='М',
            student_address='г. Москва, ул. Гагарина, д. 5',
            student_date_in=date(2021, 9, 1),
            group=groups[2] if len(groups) > 2 else groups[0]
        ),
        Student(
            student_fio='Васильева Анастасия Дмитриевна',
            student_birthday=date(2020, 11, 5),
            student_gender='Ж',
            student_address='г. Москва, ул. Мира, д. 15',
            student_date_in=date(2023, 9, 1),
            group=groups[0]
        ),
        Student(
            student_fio='Новиков Илья Петрович',
            student_birthday=date(2019, 7, 30),
            student_gender='М',
            student_address='г. Москва, ул. Садовая, д. 20',
            student_date_in=date(2022, 9, 1),
            group=groups[1] if len(groups) > 1 else groups[0]
        ),
    ]
    
    Student.objects.bulk_create(students)
    print(f"✅ Созданы {len(students)} учеников")

# 5. Родители
if Parent.objects.count() == 0:
    parents = [
        Parent(
            parent_fio='Смирнова Анна Владимировна',
            parent_number='+7-999-111-22-33'
        ),
        Parent(
            parent_fio='Кузнецов Андрей Сергеевич',
            parent_number='+7-999-222-33-44'
        ),
        Parent(
            parent_fio='Попова Елена Ивановна',
            parent_number='+7-999-333-44-55'
        ),
        Parent(
            parent_fio='Васильев Дмитрий Александрович',
            parent_number='+7-999-444-55-66'
        ),
        Parent(
            parent_fio='Новикова Ольга Сергеевна',
            parent_number='+7-999-555-66-77'
        ),
    ]
    
    Parent.objects.bulk_create(parents)
    print(f"✅ Созданы {len(parents)} родителей")

# 6. Связи ученик-родитель
if StudentParent.objects.count() == 0:
    students = Student.objects.all()
    parents = Parent.objects.all()
    
    relationships = []
    for i, student in enumerate(students):
        if i < len(parents):
            relationships.append(
                StudentParent(
                    student=student,
                    parent=parents[i],
                    relationship_type='Мать' if i % 2 == 0 else 'Отец',
                    is_primary=True
                )
            )
    
    StudentParent.objects.bulk_create(relationships)
    print(f"✅ Созданы {len(relationships)} связей ученик-родитель")

# 7. Посещаемость (опционально)
if Attendance.objects.count() == 0:
    import random
    from datetime import timedelta
    
    students = Student.objects.all()
    teachers = Teacher.objects.all()
    
    attendance_records = []
    for student in students:
        for day in range(10):  # За последние 10 дней
            attendance_date = date.today() - timedelta(days=day)
            status = random.choice([True, True, True, False])  # 75% присутствия
            
            attendance_records.append(
                Attendance(
                    attendance_date=attendance_date,
                    status=status,
                    student=student,
                    reason='' if status else random.choice(['Болезнь', 'Отпуск']),
                    noted_by=teachers[0] if teachers.exists() else None
                )
            )
    
    Attendance.objects.bulk_create(attendance_records)
    print(f"✅ Созданы {len(attendance_records)} записей о посещаемости")

print("\n🎉 База данных успешно заполнена!")
print("\n📊 Статистика:")
print(f"   • Воспитателей: {Teacher.objects.count()}")
print(f"   • Групп: {Group.objects.count()}")
print(f"   • Учеников: {Student.objects.count()}")
print(f"   • Родителей: {Parent.objects.count()}")
print(f"   • Записей посещаемости: {Attendance.objects.count()}")
print("\n🌐 Запустите сервер: python manage.py runserver")
print("🔗 Адрес: http://127.0.0.1:8000/")
print("🔑 Админка: http://127.0.0.1:8000/admin/ (admin/admin123)")