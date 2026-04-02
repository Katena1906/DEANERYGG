# services/data_service.py
from database.db import db
from database.models import (
    Student, StudentGroup, Grade, Discipline, 
    AssessmentType, AcademicDebt, Retake, 
    User, Faculty, Teacher
)
from sqlalchemy import func, and_
from datetime import datetime

def get_student_with_group(student_id: int) -> dict:
    student = Student.query.get(student_id)
    if not student:
        return None
    
    return {
        'id': student.student_id,
        'full_name': student.full_name(),
        'email': student.student_email,
        'phone': student.student_phone,
        'status': student.student_status,
        'record_book_id': student.record_book_id,
        'group_id': student.group_id,
        'group_name': student.group.group_name if student.group else 'Не указана'
    }

def get_student_grades(student_id: int, limit: int = None) -> list:
    query = Grade.query.filter_by(student_id=student_id).order_by(Grade.record_date.desc())
    
    if limit:
        query = query.limit(limit)
    
    grades = query.all()
    result = []
    
    for grade in grades:
        result.append({
            'id': grade.grade_id,
            'discipline_name': grade.discipline.discipline_name if grade.discipline else '—',
            'grade_value': grade.grade_value,
            'assessment_type': grade.assessment_type.assessment_type_name if grade.assessment_type else '—',
            'record_date': grade.record_date,
            'is_final': grade.is_final
        })
    
    return result

def get_student_debts(student_id: int, active_only: bool = True) -> list:
    query = AcademicDebt.query.filter_by(student_id=student_id)
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    debts = query.order_by(AcademicDebt.creation_date.desc()).all()
    result = []
    
    for debt in debts:
        result.append({
            'id': debt.debt_id,
            'discipline_name': debt.discipline.discipline_name if debt.discipline else '—',
            'grade_value': debt.grade.grade_value if debt.grade else '—',
            'creation_date': debt.creation_date,
            'debt_status': debt.debt_status
        })
    
    return result

def get_grade_with_details(grade_id: int) -> dict:
    grade = Grade.query.get(grade_id)
    if not grade:
        return None
    
    return {
        'id': grade.grade_id,
        'student_id': grade.student_id,
        'student_name': grade.student.full_name() if grade.student else '—',
        'discipline_id': grade.discipline_id,
        'discipline_name': grade.discipline.discipline_name if grade.discipline else '—',
        'assessment_type_id': grade.assessment_type_id,
        'assessment_type_name': grade.assessment_type.assessment_type_name if grade.assessment_type else '—',
        'grade_value': grade.grade_value,
        'is_final': grade.is_final,
        'record_date': grade.record_date,
        'teacher_comment': grade.teacher_comment
    }

def create_grade_with_debt(data: dict) -> Grade:
    grade = Grade(
        student_id=data['student_id'],
        discipline_id=data['discipline_id'],
        semester_id=data.get('semester_id', 1),
        event_id=data.get('event_id'),
        teacher_id=data.get('teacher_id'),
        assessment_type_id=data['assessment_type_id'],
        grade_value=data['grade_value'],
        is_final=data.get('is_final', False),
        teacher_comment=data.get('teacher_comment')
    )
    db.session.add(grade)
    db.session.flush()
    
    # Создаём долг, если оценка неудовлетворительная
    if not grade.is_satisfactory():
        debt = AcademicDebt(
            grade_id=grade.grade_id,
            student_id=grade.student_id,
            discipline_id=grade.discipline_id,
            semester_id=grade.semester_id,
            event_id=grade.event_id,
            is_active=True,
            debt_status='активный'
        )
        db.session.add(debt)
    
    db.session.commit()
    return grade

def close_debt_with_retake(debt_id: int, grade_value: str, teacher_id: int = None) -> Retake:
    debt = AcademicDebt.query.get(debt_id)
    if not debt or not debt.is_active:
        raise ValueError("Долг не найден или уже закрыт")
    
    # Создаём новую оценку за пересдачу
    grade = Grade(
        student_id=debt.student_id,
        discipline_id=debt.discipline_id,
        semester_id=debt.semester_id,
        event_id=debt.event_id,
        teacher_id=teacher_id,
        assessment_type_id=1,  # по умолчанию экзамен
        grade_value=grade_value,
        is_final=True
    )
    db.session.add(grade)
    db.session.flush()
    
    # Создаём запись о пересдаче
    retake = Retake(
        academic_debt_id=debt.debt_id,
        event_id=debt.event_id,
        teacher_id=teacher_id,
        assessment_type_id=1,
        result_grade_id=grade.grade_id,
        attempt_number=1,
        notification_sent=True,
        scheduled_date=datetime.utcnow(),
        retake_notes=f"Пересдача закрыта {datetime.utcnow().date()}"
    )
    db.session.add(retake)
    
    # Закрываем долг
    debt.is_active = False
    debt.debt_status = 'погашен'
    debt.resolution_date = datetime.utcnow().date()
    
    db.session.commit()
    return retake

def get_teacher_groups(teacher_id: int) -> list:
    """Получение групп, в которых преподаёт учитель"""
    # Это упрощённая версия, в реальности нужно связывать teacher -> disciplines -> groups
    return StudentGroup.query.filter_by(is_active=True).limit(10).all()

def get_group_students(group_id: int) -> list:
    """Получение студентов группы"""
    return Student.query.filter_by(group_id=group_id).all()

def get_faculty_groups(faculty_id: int) -> list:
    """Получение групп факультета"""
    return StudentGroup.query.filter_by(faculty_id=faculty_id, is_active=True).all()

def get_faculty_stats(faculty_id: int) -> dict:
    """Статистика по факультету"""
    groups = StudentGroup.query.filter_by(faculty_id=faculty_id).all()
    group_ids = [g.group_id for g in groups]
    
    students = Student.query.filter(Student.group_id.in_(group_ids)).count()
    active_students = Student.query.filter(
        Student.group_id.in_(group_ids),
        Student.student_status == 'active'
    ).count()
    
    # Средний балл по факультету
    avg_grade = db.session.query(func.avg(Grade.grade_value))\
        .join(Student, Grade.student_id == Student.student_id)\
        .filter(Student.group_id.in_(group_ids))\
        .filter(Grade.grade_value.cast(db.String).notin_(['зачет', 'незачет', 'отлично', 'хорошо', 'удовлетворительно']))\
        .scalar()
    
    # Активные долги
    active_debts = AcademicDebt.query\
        .join(Student, AcademicDebt.student_id == Student.student_id)\
        .filter(Student.group_id.in_(group_ids))\
        .filter(AcademicDebt.is_active == True)\
        .count()
    
    return {
        'total_students': students,
        'active_students': active_students,
        'groups_count': len(groups),
        'avg_grade': float(avg_grade) if avg_grade else None,
        'active_debts': active_debts
    }

def get_system_statistics() -> dict:
    from database.models import User, Student, Teacher, Faculty, StudentGroup, Discipline, Grade, AcademicDebt, Retake
    from sqlalchemy import func, cast, Float
    
    stats = {
        'users_count': User.query.count(),
        'users_by_role': {
            'student': User.query.filter_by(role='student').count(),
            'teacher': User.query.filter_by(role='teacher').count(),
            'dean': User.query.filter_by(role='dean').count(),
            'admin': User.query.filter_by(role='admin').count()
        },
        'students_count': Student.query.count(),
        'teachers_count': Teacher.query.count(),
        'faculties_count': Faculty.query.count(),
        'groups_count': StudentGroup.query.count(),
        'disciplines_count': Discipline.query.count(),
        'grades_count': Grade.query.count(),
        'active_debts_count': AcademicDebt.query.filter_by(is_active=True).count(),
        'resolved_debts_count': AcademicDebt.query.filter_by(is_active=False).count(),
        'retakes_count': Retake.query.count(),
        'avg_grade': None
    }
    
    numeric_grades = Grade.query.filter(
        Grade.grade_value.in_(['2', '3', '4', '5'])
    ).all()
    
    if numeric_grades:
        total = sum(int(g.grade_value) for g in numeric_grades)
        stats['avg_grade'] = round(total / len(numeric_grades), 2)
    
    return stats