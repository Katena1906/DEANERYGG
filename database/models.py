from database.db import db
from datetime import datetime

# ============================================================
# НОВАЯ ТАБЛИЦА ДЛЯ АУТЕНТИФИКАЦИИ
# ============================================================

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # student, teacher, dean, admin
    related_id = db.Column(db.Integer, nullable=True)  # student_id / teacher_id / faculty_id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    failed_attempts = db.Column(db.Integer, default=0)
    last_failed = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}')>"

# ============================================================
# СУЩЕСТВУЮЩИЕ ТАБЛИЦЫ
# ============================================================

class Student(db.Model):
    __tablename__ = 'student'
    
    student_id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    student_surname = db.Column(db.String(100), nullable=False)
    student_patronymic = db.Column(db.String(100))
    record_book_id = db.Column(db.String(50), unique=True, nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    student_email = db.Column(db.String(100))
    student_phone = db.Column(db.String(20))
    group_id = db.Column(db.Integer, nullable=False)
    enrollment_order_id = db.Column(db.Integer)
    education_form_id = db.Column(db.Integer)
    student_status = db.Column(db.String(50), nullable=False)
    
    def full_name(self):
        return f"{self.student_surname} {self.student_name} {self.student_patronymic or ''}".strip()
    
    def __repr__(self):
        return f"<Student(id={self.student_id}, name='{self.student_surname}')>"

class Teacher(db.Model):
    __tablename__ = 'teacher'
    
    teacher_id = db.Column(db.Integer, primary_key=True)
    teacher_surname = db.Column(db.String(100), nullable=False)
    teacher_name = db.Column(db.String(100), nullable=False)
    teacher_patronymic = db.Column(db.String(100))
    teacher_birth_date = db.Column(db.Date, nullable=False)
    teacher_gender = db.Column(db.String(10))
    teacher_email = db.Column(db.String(100))
    teacher_phone = db.Column(db.String(20))
    position_id = db.Column(db.Integer)
    degree_id = db.Column(db.Integer)
    department_id = db.Column(db.Integer)
    can_create_events = db.Column(db.Boolean, default=False)
    
    def full_name(self):
        return f"{self.teacher_surname} {self.teacher_name} {self.teacher_patronymic or ''}".strip()
    
    def __repr__(self):
        return f"<Teacher(id={self.teacher_id}, name='{self.teacher_surname}')>"

class Faculty(db.Model):
    __tablename__ = 'faculty'
    
    faculty_id = db.Column(db.Integer, primary_key=True)
    faculty_name = db.Column(db.String(100), nullable=False)
    dean_name = db.Column(db.String(100), nullable=False)
    dean_surname = db.Column(db.String(100), nullable=False)
    dean_patronymic = db.Column(db.String(100))
    faculty_phone = db.Column(db.String(20))
    faculty_email = db.Column(db.String(100))
    
    def dean_full_name(self):
        return f"{self.dean_surname} {self.dean_name} {self.dean_patronymic or ''}".strip()
    
    def __repr__(self):
        return f"<Faculty(id={self.faculty_id}, name='{self.faculty_name}')>"



# ============================================================
# УСПЕВАЕМОСТЬ
# ============================================================

class Grade(db.Model):
    __tablename__ = 'grade'
    
    grade_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    discipline_id = db.Column(db.Integer, nullable=False)
    semester_id = db.Column(db.Integer, nullable=False)
    event_id = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.teacher_id'), nullable=False)
    grade_sheet_id = db.Column(db.Integer)
    assessment_type_id = db.Column(db.Integer, db.ForeignKey('assessment_type.assessment_type_id'))
    grade_value = db.Column(db.String(10), nullable=False)
    is_final = db.Column(db.Boolean, default=False)
    record_date = db.Column(db.DateTime, default=datetime.utcnow)
    teacher_comment = db.Column(db.Text)
    
    def __repr__(self):
        return f"<Grade(id={self.grade_id}, value='{self.grade_value}')>"

class AcademicDebt(db.Model):
    __tablename__ = 'academic_debt'
    
    debt_id = db.Column(db.Integer, primary_key=True)
    grade_id = db.Column(db.Integer, db.ForeignKey('grade.grade_id'), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    discipline_id = db.Column(db.Integer, nullable=False)
    semester_id = db.Column(db.Integer, nullable=False)
    event_id = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    debt_status = db.Column(db.String(30))
    resolution_date = db.Column(db.Date)
    admin_comment = db.Column(db.Text)
    
    def __repr__(self):
        return f"<AcademicDebt(id={self.debt_id}, active={self.is_active})>"

class Retake(db.Model):
    __tablename__ = 'retake'
    
    retake_id = db.Column(db.Integer, primary_key=True)
    academic_debt_id = db.Column(db.Integer, db.ForeignKey('academic_debt.debt_id'), nullable=False)
    event_id = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.teacher_id'), nullable=False)
    assessment_type_id = db.Column(db.Integer, db.ForeignKey('assessment_type.assessment_type_id'), nullable=False)
    result_grade_id = db.Column(db.Integer, db.ForeignKey('grade.grade_id'), nullable=True)
    attempt_number = db.Column(db.Integer, nullable=False)
    notification_sent = db.Column(db.Boolean, default=False)
    scheduled_date = db.Column(db.DateTime)
    retake_notes = db.Column(db.Text)
    
    def __repr__(self):
        return f"<Retake(id={self.retake_id}, attempt={self.attempt_number})>"

class AssessmentType(db.Model):
    __tablename__ = 'assessment_type'
    
    assessment_type_id = db.Column(db.Integer, primary_key=True)
    assessment_type_name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f"<AssessmentType(id={self.assessment_type_id}, name='{self.assessment_type_name}')>"

# ============================================================
# МЕРОПРИЯТИЯ
# ============================================================

class EventType(db.Model):
    __tablename__ = 'event_type'
    
    event_type_id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(150), nullable=False, unique=True)
    importance_level = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f"<EventType(id={self.event_type_id}, type='{self.type_name}')>"

class Event(db.Model):
    __tablename__ = 'event'
    
    event_id = db.Column(db.Integer, primary_key=True)
    event_type_id = db.Column(db.Integer, db.ForeignKey('event_type.event_type_id'), nullable=False)
    discipline_id = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.teacher_id'), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.Time, nullable=False)
    event_location = db.Column(db.String(200))
    auto_reminder = db.Column(db.Boolean, default=False)
    event_name = db.Column(db.String(300))
    
    type = db.relationship('EventType', backref=db.backref('events', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('organized_events', lazy=True))
    
    def __repr__(self):
        return f"<Event(id={self.event_id}, name='{self.event_name}')>"

class EventCoauthor(db.Model):
    __tablename__ = 'event_coauthor'
    
    coauthor_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.event_id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.teacher_id'), nullable=False)
    can_modify = db.Column(db.Boolean, default=False)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    event = db.relationship('Event', backref=db.backref('coauthors', lazy=True))
    teacher = db.relationship('Teacher', backref=db.backref('coauthored_events', lazy=True))
    
    def __repr__(self):
        return f"<EventCoauthor(event_id={self.event_id}, teacher_id={self.teacher_id})>"

class Notification(db.Model):
    __tablename__ = 'notification'
    
    notification_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.event_id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    notification_type = db.Column(db.String(50))
    message = db.Column(db.Text)
    sent_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    event = db.relationship('Event', backref=db.backref('notifications', lazy=True))
    student = db.relationship('Student', backref=db.backref('notifications', lazy=True))
    
    def __repr__(self):
        return f"<Notification(id={self.notification_id}, type='{self.notification_type}')>"

class Deadline(db.Model):
    __tablename__ = 'deadline'
    
    deadline_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.event_id'), nullable=False)
    discipline_id = db.Column(db.Integer, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    deadline_date = db.Column(db.Date, nullable=False)
    deadline_priority = db.Column(db.String(20))
    deadline_status = db.Column(db.String(20))
    
    event = db.relationship('Event', backref=db.backref('deadlines', lazy=True))
    student = db.relationship('Student', backref=db.backref('deadlines', lazy=True))
    
    def __repr__(self):
        return f"<Deadline(id={self.deadline_id}, status='{self.deadline_status}')>"
