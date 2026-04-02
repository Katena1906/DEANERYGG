# blueprints/admin.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from decorators.auth import login_required, role_required
from services.auth_service import get_user_by_id, hash_password
from services.authz_service import get_available_actions, ROLE_PERMISSIONS
from services.data_service import get_system_statistics
from database.models import User, Student, Teacher, Faculty, StudentGroup
from database.db import db
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/panel')
@login_required
@role_required('admin')
def panel():
    user = get_user_by_id(session['user_id'])
    actions = get_available_actions(user)
    stats = get_system_statistics()
    
    return render_template('admin/panel.html',
                         user=user,
                         actions=actions,
                         stats=stats)

@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    user = get_user_by_id(session['user_id'])
    all_users = User.query.order_by(User.created_at.desc()).all()
    
    return render_template('admin/users.html',
                         user=user,
                         users=all_users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_user():
    user = get_user_by_id(session['user_id'])
    
    if request.method == 'GET':
        return render_template('admin/create_user.html', user=user)
    
    # POST - создание пользователя
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    
    # Проверка на существующего пользователя
    if User.query.filter_by(email=email).first():
        flash('Пользователь с таким email уже существует', 'error')
        return redirect(url_for('admin.create_user'))
    
    if not email or not password or not role:
        flash('Все поля обязательны для заполнения', 'error')
        return redirect(url_for('admin.create_user'))
    
    related_id = None
    
    # Обработка СТУДЕНТА
    if role == 'student':
        group_name = request.form.get('group_name')
        record_book_id = request.form.get('record_book_id')
        
        # Проверяем существование группы
        group = StudentGroup.query.filter_by(group_name=group_name).first()
        if not group:
            flash(f'Группа "{group_name}" не найдена в системе', 'error')
            return redirect(url_for('admin.create_user'))
        
        # Проверяем уникальность зачетной книжки
        if Student.query.filter_by(record_book_id=record_book_id).first():
            flash(f'Студент с зачетной книжкой {record_book_id} уже существует', 'error')
            return redirect(url_for('admin.create_user'))
        
        # Создаем студента
        try:
            birth_date = datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d').date()
        except:
            flash('Неверный формат даты рождения', 'error')
            return redirect(url_for('admin.create_user'))
        
        new_student = Student(
            student_surname=request.form.get('student_surname'),
            student_name=request.form.get('student_name'),
            student_patronymic=request.form.get('student_patronymic'),
            record_book_id=record_book_id,
            birth_date=birth_date,
            student_email=request.form.get('student_email_contact'),
            student_phone=request.form.get('student_phone'),
            group_id=group.group_id,
            student_status='активный'
        )
        db.session.add(new_student)
        db.session.flush()
        related_id = new_student.student_id
    
    # Обработка ПРЕПОДАВАТЕЛЯ
    elif role == 'teacher':
        try:
            birth_date = datetime.strptime(request.form.get('teacher_birth_date'), '%Y-%m-%d').date()
        except:
            flash('Неверный формат даты рождения', 'error')
            return redirect(url_for('admin.create_user'))
        
        # Проверяем уникальность email преподавателя
        if Teacher.query.filter_by(teacher_email=request.form.get('teacher_email_contact')).first():
            flash('Преподаватель с таким email уже существует', 'error')
            return redirect(url_for('admin.create_user'))
        
        new_teacher = Teacher(
            teacher_surname=request.form.get('teacher_surname'),
            teacher_name=request.form.get('teacher_name'),
            teacher_patronymic=request.form.get('teacher_patronymic'),
            teacher_birth_date=birth_date,
            teacher_email=request.form.get('teacher_email_contact'),
            teacher_phone=request.form.get('teacher_phone'),
            department_id=None,
            can_create_events=False
        )
        db.session.add(new_teacher)
        db.session.flush()
        related_id = new_teacher.teacher_id
    
    # Обработка ДЕКАНАТА
    elif role == 'dean':
        faculty_name = request.form.get('faculty_name')
        
        # Проверяем существование факультета
        faculty = Faculty.query.filter_by(faculty_name=faculty_name).first()
        if not faculty:
            flash(f'Факультет "{faculty_name}" не найден в системе', 'error')
            return redirect(url_for('admin.create_user'))
        
        # Обновляем данные декана
        faculty.dean_surname = request.form.get('dean_surname')
        faculty.dean_name = request.form.get('dean_name')
        faculty.dean_patronymic = request.form.get('dean_patronymic')
        faculty.faculty_phone = request.form.get('faculty_phone')
        faculty.faculty_email = request.form.get('faculty_email')
        db.session.commit()
        related_id = faculty.faculty_id
    
    # Создаем пользователя
    new_user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        related_id=related_id
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    flash(f'Пользователь {email} успешно создан с ролью {role}', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/edit')
@login_required
@role_required('admin')
def edit_user(user_id):
    user = get_user_by_id(session['user_id'])
    edit_user = User.query.get_or_404(user_id)
    
    return render_template('admin/edit_user.html',
                         user=user,
                         edit_user=edit_user)

@admin_bp.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
@role_required('admin')
def update_user(user_id):
    edit_user = User.query.get_or_404(user_id)
    
    email = request.form.get('email')
    role = request.form.get('role')
    new_password = request.form.get('password')
    
    edit_user.email = email
    edit_user.role = role
    
    if new_password:
        edit_user.password_hash = hash_password(new_password)
    
    db.session.commit()
    flash('Пользователь обновлен', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.user_id == session['user_id']:
        flash('Нельзя удалить свою учетную запись', 'error')
        return redirect(url_for('admin.users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('Пользователь удален', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/roles')
@login_required
@role_required('admin')
def roles():
    user = get_user_by_id(session['user_id'])
    actions = get_available_actions(user)
    stats = get_system_statistics()
    
    return render_template('admin/roles.html',
                         user=user,
                         actions=actions,
                         stats=stats,
                         role_permissions=ROLE_PERMISSIONS,
                         users_by_role=stats.get('users_by_role', {}))

@admin_bp.route('/statistics')
@login_required
@role_required('admin')
def statistics():
    user = get_user_by_id(session['user_id'])
    actions = get_available_actions(user)
    stats = get_system_statistics()
    
    return render_template('admin/statistics.html',
                         user=user,
                         actions=actions,
                         stats=stats)