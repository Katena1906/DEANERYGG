from flask import Flask, request, jsonify
from functools import wraps
from database.db import init_db, db
from database.models import User, Student, Teacher, Faculty, Grade, AcademicDebt, Retake
from services.auth_service import authenticate, get_user_by_id, get_profile_by_user, identify_user, is_account_locked, hash_password
from services.authz_service import has_permission, get_user_permissions, get_available_actions, get_role_info
import jwt
from datetime import datetime, timedelta
from sqlalchemy import func
from flask import send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True, origins='*')
init_db(app)

# Отдача фронтенда
@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')

# Отдача статических файлов (CSS, GIF)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# JWT настройки
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET', 'fallback-secret-key')
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))


# ============================================================
# API ДЕКОРАТОРЫ
# ============================================================

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Требуется авторизация'}), 401
        
        try:
            token = auth_header.replace('Bearer ', '')
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            request.user_id = payload['user_id']
            request.user_role = payload['role']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Токен истёк'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Неверный токен'}), 401
        
        return f(*args, **kwargs)
    return decorated_function


def api_role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'user_role'):
                return jsonify({'error': 'Не авторизован'}), 401
            if request.user_role not in roles:
                return jsonify({'error': 'Недостаточно прав'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def api_permission_required(resource, action):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'user_id'):
                return jsonify({'error': 'Не авторизован'}), 401
            
            user = get_user_by_id(request.user_id)
            if not user or not has_permission(user, resource, action):
                return jsonify({'error': f'Недостаточно прав: {resource}/{action}'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================
# АУТЕНТИФИКАЦИЯ
# ============================================================

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def api_login():
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Ожидается JSON'}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email и пароль обязательны'}), 400
    
    user_check = identify_user(email)
    
    # Проверка блокировки
    if user_check and is_account_locked(user_check):
        return jsonify({
            'error': 'Аккаунт заблокирован на 5 минут',
            'locked': True,
            'attempts_left': 0
        }), 403
    
    user = authenticate(email, password)
    
    if not user:
        # Подсчёт оставшихся попыток
        attempts_left = 3
        if user_check:
            failed = user_check.failed_attempts or 0
            attempts_left = 3 - failed
            if attempts_left < 0:
                attempts_left = 0
        
        return jsonify({
            'error': 'Неверный email или пароль',
            'attempts_left': attempts_left,
            'locked': False
        }), 401
    
    token = jwt.encode({
        'user_id': user.user_id,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }, JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user.user_id,
            'email': user.email,
            'role': user.role
        }
    })


@app.route('/api/logout', methods=['POST'])
@api_login_required
def api_logout():
    return jsonify({'success': True})


@app.route('/api/me', methods=['GET'])
@api_login_required
def api_me():
    user = get_user_by_id(request.user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    profile = get_profile_by_user(user)
    permissions = get_user_permissions(user)
    
    return jsonify({
        'user': {
            'id': user.user_id,
            'email': user.email,
            'role': user.role,
            'profile': {
                'full_name': profile.full_name() if profile else None
            } if profile else None
        },
        'permissions': permissions,
        'available_actions': get_available_actions(user),
        'role_info': get_role_info(user)
    })


# ============================================================
# ПОЛЬЗОВАТЕЛИ (только админ)
# ============================================================

@app.route('/api/users', methods=['GET'])
@api_login_required
@api_permission_required('users', 'read')
def api_users_list():
    users = User.query.all()
    return jsonify({
        'users': [{
            'id': u.user_id,
            'email': u.email,
            'role': u.role,
            'related_id': u.related_id,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'last_login': u.last_login.isoformat() if u.last_login else None
        } for u in users]
    })


@app.route('/api/users/<int:user_id>', methods=['GET'])
@api_login_required
@api_permission_required('users', 'read')
def api_users_get(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    return jsonify({
        'user': {
            'id': user.user_id,
            'email': user.email,
            'role': user.role,
            'related_id': user.related_id,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
    })


@app.route('/api/users', methods=['POST'])
@api_login_required
@api_permission_required('users', 'create')
def api_users_create():
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'student')
    related_id = data.get('related_id')
    
    if not email or not password:
        return jsonify({'error': 'Email и пароль обязательны'}), 400
    
    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'Пользователь уже существует'}), 400
    
    try:
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            related_id=related_id
        )
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'user': {'id': user.user_id, 'email': user.email, 'role': user.role}
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@api_login_required
@api_permission_required('users', 'update')
def api_users_update(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    data = request.get_json()
    
    if 'email' in data:
        user.email = data['email']
    if 'role' in data:
        user.role = data['role']
    if 'related_id' in data:
        user.related_id = data['related_id']
    if 'password' in data:
        user.password_hash = hash_password(data['password'])
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': {'id': user.user_id, 'email': user.email, 'role': user.role}
    })


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@api_login_required
@api_permission_required('users', 'delete')
def api_users_delete(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True})


# ============================================================
# СТУДЕНТЫ
# ============================================================

@app.route('/api/students', methods=['GET'])
@api_login_required
def api_students_list():
    user = get_user_by_id(request.user_id)
    
    if has_permission(user, 'students', 'read_all'):
        students = Student.query.all()
    elif has_permission(user, 'students', 'read'):
        students = Student.query.all()
    else:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    return jsonify({
        'students': [{
            'id': s.student_id,
            'full_name': s.full_name(),
            'email': s.student_email,
            'phone': s.student_phone,
            'status': s.student_status,
            'record_book_id': s.record_book_id,
            'group_id': s.group_id
        } for s in students]
    })


@app.route('/api/students/<int:student_id>', methods=['GET'])
@api_login_required
def api_students_get(student_id):
    user = get_user_by_id(request.user_id)
    student = Student.query.get(student_id)
    
    if not student:
        return jsonify({'error': 'Студент не найден'}), 404
    
    can_read = False
    if has_permission(user, 'students', 'read_all'):
        can_read = True
    elif has_permission(user, 'students', 'read'):
        can_read = True
    elif user.role == 'student' and user.related_id == student_id:
        can_read = True
    
    if not can_read:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    return jsonify({
        'student': {
            'id': student.student_id,
            'full_name': student.full_name(),
            'email': student.student_email,
            'phone': student.student_phone,
            'status': student.student_status,
            'record_book_id': student.record_book_id,
            'group_id': student.group_id,
            'birth_date': student.birth_date.isoformat() if student.birth_date else None
        }
    })


@app.route('/api/students', methods=['POST'])
@api_login_required
@api_role_required('dean', 'admin')
def api_students_create():
    data = request.get_json()
    
    required = ['student_name', 'student_surname', 'record_book_id', 'birth_date', 'group_id', 'student_status']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    birth_date = datetime.fromisoformat(data['birth_date']).date()
    
    student = Student(
        student_name=data['student_name'],
        student_surname=data['student_surname'],
        student_patronymic=data.get('student_patronymic'),
        record_book_id=data['record_book_id'],
        birth_date=birth_date,
        student_email=data.get('student_email'),
        student_phone=data.get('student_phone'),
        group_id=data['group_id'],
        enrollment_order_id=data.get('enrollment_order_id'),
        education_form_id=data.get('education_form_id'),
        student_status=data['student_status']
    )
    
    db.session.add(student)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'student': {'id': student.student_id, 'full_name': student.full_name()}
    }), 201


@app.route('/api/students/<int:student_id>', methods=['PUT'])
@api_login_required
@api_role_required('dean', 'admin')
def api_students_update(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Студент не найден'}), 404
    
    data = request.get_json()
    
    if 'student_name' in data:
        student.student_name = data['student_name']
    if 'student_surname' in data:
        student.student_surname = data['student_surname']
    if 'student_patronymic' in data:
        student.student_patronymic = data['student_patronymic']
    if 'student_email' in data:
        student.student_email = data['student_email']
    if 'student_phone' in data:
        student.student_phone = data['student_phone']
    if 'group_id' in data:
        student.group_id = data['group_id']
    if 'student_status' in data:
        student.student_status = data['student_status']
    
    db.session.commit()
    
    return jsonify({'success': True, 'student': {'id': student.student_id, 'full_name': student.full_name()}})


@app.route('/api/students/<int:student_id>', methods=['DELETE'])
@api_login_required
@api_role_required('admin')
def api_students_delete(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Студент не найден'}), 404
    
    db.session.delete(student)
    db.session.commit()
    
    return jsonify({'success': True})


# ============================================================
# ПРЕПОДАВАТЕЛИ
# ============================================================

@app.route('/api/teachers', methods=['GET'])
@api_login_required
def api_teachers_list():
    user = get_user_by_id(request.user_id)
    
    if user.role not in ['admin', 'dean']:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    teachers = Teacher.query.all()
    return jsonify({
        'teachers': [{
            'id': t.teacher_id,
            'full_name': t.full_name(),
            'email': t.teacher_email,
            'phone': t.teacher_phone,
            'can_create_events': t.can_create_events
        } for t in teachers]
    })


@app.route('/api/teachers/<int:teacher_id>', methods=['GET'])
@api_login_required
def api_teachers_get(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({'error': 'Преподаватель не найден'}), 404
    
    user = get_user_by_id(request.user_id)
    if user.role not in ['admin', 'dean'] and user.related_id != teacher_id:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    return jsonify({
        'teacher': {
            'id': teacher.teacher_id,
            'full_name': teacher.full_name(),
            'email': teacher.teacher_email,
            'phone': teacher.teacher_phone,
            'position_id': teacher.position_id,
            'degree_id': teacher.degree_id,
            'department_id': teacher.department_id,
            'can_create_events': teacher.can_create_events
        }
    })


@app.route('/api/teachers', methods=['POST'])
@api_login_required
@api_role_required('admin')
def api_teachers_create():
    data = request.get_json()
    
    required = ['teacher_name', 'teacher_surname', 'teacher_birth_date']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    birth_date = datetime.fromisoformat(data['teacher_birth_date']).date()
    
    teacher = Teacher(
        teacher_name=data['teacher_name'],
        teacher_surname=data['teacher_surname'],
        teacher_patronymic=data.get('teacher_patronymic'),
        teacher_birth_date=birth_date,
        teacher_gender=data.get('teacher_gender'),
        teacher_email=data.get('teacher_email'),
        teacher_phone=data.get('teacher_phone'),
        position_id=data.get('position_id'),
        degree_id=data.get('degree_id'),
        department_id=data.get('department_id'),
        can_create_events=data.get('can_create_events', False)
    )
    
    db.session.add(teacher)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'teacher': {'id': teacher.teacher_id, 'full_name': teacher.full_name()}
    }), 201


@app.route('/api/teachers/<int:teacher_id>', methods=['PUT'])
@api_login_required
@api_role_required('admin')
def api_teachers_update(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({'error': 'Преподаватель не найден'}), 404
    
    data = request.get_json()
    
    if 'teacher_name' in data:
        teacher.teacher_name = data['teacher_name']
    if 'teacher_surname' in data:
        teacher.teacher_surname = data['teacher_surname']
    if 'teacher_patronymic' in data:
        teacher.teacher_patronymic = data['teacher_patronymic']
    if 'teacher_email' in data:
        teacher.teacher_email = data['teacher_email']
    if 'teacher_phone' in data:
        teacher.teacher_phone = data['teacher_phone']
    if 'can_create_events' in data:
        teacher.can_create_events = data['can_create_events']
    
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/teachers/<int:teacher_id>', methods=['DELETE'])
@api_login_required
@api_role_required('admin')
def api_teachers_delete(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({'error': 'Преподаватель не найден'}), 404
    
    db.session.delete(teacher)
    db.session.commit()
    
    return jsonify({'success': True})


# ============================================================
# ФАКУЛЬТЕТЫ
# ============================================================

@app.route('/api/faculties', methods=['GET'])
@api_login_required
def api_faculties_list():
    faculties = Faculty.query.all()
    return jsonify({
        'faculties': [{
            'id': f.faculty_id,
            'name': f.faculty_name,
            'dean_full_name': f.dean_full_name(),
            'email': f.faculty_email,
            'phone': f.faculty_phone
        } for f in faculties]
    })


@app.route('/api/faculties/<int:faculty_id>', methods=['GET'])
@api_login_required
def api_faculties_get(faculty_id):
    faculty = Faculty.query.get(faculty_id)
    if not faculty:
        return jsonify({'error': 'Факультет не найден'}), 404
    
    return jsonify({
        'faculty': {
            'id': faculty.faculty_id,
            'name': faculty.faculty_name,
            'dean_name': faculty.dean_name,
            'dean_surname': faculty.dean_surname,
            'dean_patronymic': faculty.dean_patronymic,
            'email': faculty.faculty_email,
            'phone': faculty.faculty_phone
        }
    })


@app.route('/api/faculties', methods=['POST'])
@api_login_required
@api_role_required('admin')
def api_faculties_create():
    data = request.get_json()
    
    if not data.get('faculty_name') or not data.get('dean_name') or not data.get('dean_surname'):
        return jsonify({'error': 'Название факультета и ФИО декана обязательны'}), 400
    
    faculty = Faculty(
        faculty_name=data['faculty_name'],
        dean_name=data['dean_name'],
        dean_surname=data['dean_surname'],
        dean_patronymic=data.get('dean_patronymic'),
        faculty_email=data.get('faculty_email'),
        faculty_phone=data.get('faculty_phone')
    )
    
    db.session.add(faculty)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'faculty': {'id': faculty.faculty_id, 'name': faculty.faculty_name}
    }), 201


@app.route('/api/faculties/<int:faculty_id>', methods=['PUT'])
@api_login_required
@api_role_required('admin')
def api_faculties_update(faculty_id):
    faculty = Faculty.query.get(faculty_id)
    if not faculty:
        return jsonify({'error': 'Факультет не найден'}), 404
    
    data = request.get_json()
    
    if 'faculty_name' in data:
        faculty.faculty_name = data['faculty_name']
    if 'dean_name' in data:
        faculty.dean_name = data['dean_name']
    if 'dean_surname' in data:
        faculty.dean_surname = data['dean_surname']
    if 'dean_patronymic' in data:
        faculty.dean_patronymic = data['dean_patronymic']
    if 'faculty_email' in data:
        faculty.faculty_email = data['faculty_email']
    if 'faculty_phone' in data:
        faculty.faculty_phone = data['faculty_phone']
    
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/faculties/<int:faculty_id>', methods=['DELETE'])
@api_login_required
@api_role_required('admin')
def api_faculties_delete(faculty_id):
    faculty = Faculty.query.get(faculty_id)
    if not faculty:
        return jsonify({'error': 'Факультет не найден'}), 404
    
    db.session.delete(faculty)
    db.session.commit()
    
    return jsonify({'success': True})


# ============================================================
# ОЦЕНКИ
# ============================================================

@app.route('/api/grades', methods=['GET'])
@api_login_required
def api_grades_list():
    user = get_user_by_id(request.user_id)
    
    student_id = request.args.get('student_id', type=int)
    discipline_id = request.args.get('discipline_id', type=int)
    
    query = Grade.query
    
    if has_permission(user, 'grades', 'read_all'):
        pass
    elif has_permission(user, 'grades', 'read_own'):
        if user.role == 'student':
            query = query.filter_by(student_id=user.related_id)
    elif has_permission(user, 'grades', 'read'):
        if user.role == 'teacher' and user.related_id:
            query = query.filter_by(teacher_id=user.related_id)
    else:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    if student_id:
        query = query.filter_by(student_id=student_id)
    if discipline_id:
        query = query.filter_by(discipline_id=discipline_id)
    
    grades = query.order_by(Grade.record_date.desc()).all()
    
    return jsonify({
        'grades': [{
            'id': g.grade_id,
            'student_id': g.student_id,
            'discipline_id': g.discipline_id,
            'grade_value': g.grade_value,
            'is_final': g.is_final,
            'record_date': g.record_date.isoformat() if g.record_date else None,
            'teacher_comment': g.teacher_comment
        } for g in grades]
    })


@app.route('/api/grades', methods=['POST'])
@api_login_required
@api_permission_required('grades', 'create')
def api_grades_create():
    data = request.get_json()
    
    required = ['student_id', 'discipline_id', 'semester_id', 'event_id', 'assessment_type_id', 'grade_value']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    user = get_user_by_id(request.user_id)
    
    grade = Grade(
        student_id=data['student_id'],
        discipline_id=data['discipline_id'],
        semester_id=data['semester_id'],
        event_id=data['event_id'],
        teacher_id=user.related_id if user.role == 'teacher' else data.get('teacher_id'),
        assessment_type_id=data['assessment_type_id'],
        grade_value=data['grade_value'],
        is_final=data.get('is_final', False),
        teacher_comment=data.get('teacher_comment')
    )
    
    db.session.add(grade)
    db.session.commit()
    
    if grade.grade_value in ['2', 'неудовлетворительно', 'незачет']:
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
    
    return jsonify({
        'success': True,
        'grade': {'id': grade.grade_id, 'grade_value': grade.grade_value}
    }), 201


@app.route('/api/grades/<int:grade_id>', methods=['PUT'])
@api_login_required
@api_permission_required('grades', 'update')
def api_grades_update(grade_id):
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({'error': 'Оценка не найдена'}), 404
    
    data = request.get_json()
    
    if 'grade_value' in data:
        grade.grade_value = data['grade_value']
    if 'is_final' in data:
        grade.is_final = data['is_final']
    if 'teacher_comment' in data:
        grade.teacher_comment = data['teacher_comment']
    
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/grades/<int:grade_id>', methods=['DELETE'])
@api_login_required
@api_role_required('admin')
def api_grades_delete(grade_id):
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({'error': 'Оценка не найдена'}), 404
    
    db.session.delete(grade)
    db.session.commit()
    
    return jsonify({'success': True})


# ============================================================
# ДОЛГИ
# ============================================================

@app.route('/api/debts', methods=['GET'])
@api_login_required
def api_debts_list():
    user = get_user_by_id(request.user_id)
    
    student_id = request.args.get('student_id', type=int)
    
    query = AcademicDebt.query
    
    if has_permission(user, 'debts', 'read_all'):
        pass
    elif has_permission(user, 'debts', 'read_own'):
        if user.role == 'student':
            query = query.filter_by(student_id=user.related_id)
    else:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    if student_id:
        query = query.filter_by(student_id=student_id)
    
    debts = query.filter_by(is_active=True).order_by(AcademicDebt.creation_date.desc()).all()
    
    return jsonify({
        'debts': [{
            'id': d.debt_id,
            'student_id': d.student_id,
            'discipline_id': d.discipline_id,
            'debt_status': d.debt_status,
            'creation_date': d.creation_date.isoformat() if d.creation_date else None
        } for d in debts]
    })


@app.route('/api/debts/<int:debt_id>/close', methods=['POST'])
@api_login_required
@api_permission_required('debts', 'manage')
def api_debts_close(debt_id):
    debt = AcademicDebt.query.get(debt_id)
    if not debt:
        return jsonify({'error': 'Долг не найден'}), 404
    
    debt.is_active = False
    debt.debt_status = 'погашен'
    debt.resolution_date = datetime.utcnow().date()
    
    db.session.commit()
    
    return jsonify({'success': True})


# ============================================================
# ПЕРЕСДАЧИ
# ============================================================

@app.route('/api/retakes', methods=['GET'])
@api_login_required
def api_retakes_list():
    user = get_user_by_id(request.user_id)
    
    query = Retake.query
    
    if has_permission(user, 'retakes', 'read_all'):
        pass
    elif has_permission(user, 'retakes', 'read_own'):
        if user.role == 'student':
            debts = AcademicDebt.query.filter_by(student_id=user.related_id).all()
            debt_ids = [d.debt_id for d in debts]
            query = query.filter(Retake.academic_debt_id.in_(debt_ids))
    elif has_permission(user, 'retakes', 'read'):
        if user.role == 'teacher' and user.related_id:
            query = query.filter_by(teacher_id=user.related_id)
    else:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    retakes = query.order_by(Retake.scheduled_date.desc()).all()
    
    return jsonify({
        'retakes': [{
            'id': r.retake_id,
            'attempt_number': r.attempt_number,
            'scheduled_date': r.scheduled_date.isoformat() if r.scheduled_date else None
        } for r in retakes]
    })


@app.route('/api/retakes', methods=['POST'])
@api_login_required
@api_permission_required('retakes', 'create')
def api_retakes_create():
    data = request.get_json()
    
    required = ['academic_debt_id', 'event_id', 'assessment_type_id', 'scheduled_date']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Поле {field} обязательно'}), 400
    
    user = get_user_by_id(request.user_id)
    
    attempt_count = Retake.query.filter_by(academic_debt_id=data['academic_debt_id']).count()
    
    retake = Retake(
        academic_debt_id=data['academic_debt_id'],
        event_id=data['event_id'],
        teacher_id=user.related_id if user.role == 'teacher' else data.get('teacher_id'),
        assessment_type_id=data['assessment_type_id'],
        attempt_number=attempt_count + 1,
        scheduled_date=datetime.fromisoformat(data['scheduled_date']),
        retake_notes=data.get('retake_notes')
    )
    
    db.session.add(retake)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'retake': {'id': retake.retake_id, 'attempt_number': retake.attempt_number}
    }), 201


# ============================================================
# ОТЧЁТЫ
# ============================================================

@app.route('/api/reports/performance', methods=['GET'])
@api_login_required
@api_permission_required('reports', 'generate')
def api_reports_performance():
    grade_stats = db.session.query(
        Grade.grade_value,
        func.count(Grade.grade_id).label('count')
    ).group_by(Grade.grade_value).all()
    
    debt_stats = {
        'active': AcademicDebt.query.filter_by(is_active=True).count(),
        'resolved': AcademicDebt.query.filter_by(is_active=False).count()
    }
    
    return jsonify({
        'report': {
            'generated_at': datetime.utcnow().isoformat(),
            'grade_distribution': {g.grade_value: g.count for g in grade_stats},
            'debts': debt_stats
        }
    })


# ============================================================
# СТАТИСТИКА (админ)
# ============================================================

@app.route('/api/admin/stats', methods=['GET'])
@api_login_required
@api_role_required('admin')
def api_admin_stats():
    stats = {
        'users': User.query.count(),
        'students': Student.query.count(),
        'teachers': Teacher.query.count(),
        'faculties': Faculty.query.count(),
        'active_debts': AcademicDebt.query.filter_by(is_active=True).count(),
        'total_retakes': Retake.query.count(),
        'total_grades': Grade.query.count(),
        'users_by_role': {
            'student': User.query.filter_by(role='student').count(),
            'teacher': User.query.filter_by(role='teacher').count(),
            'dean': User.query.filter_by(role='dean').count(),
            'admin': User.query.filter_by(role='admin').count()
        }
    }
    
    return jsonify({'stats': stats})


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass