# blueprints/teacher.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from decorators.auth import login_required, role_required
from services.auth_service import get_user_by_id, get_profile_by_user
from services.authz_service import get_available_actions, has_permission
from services.data_service import get_teacher_groups, get_group_students
from database.models import Student, Grade, Discipline, AssessmentType
from database.db import db

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

@teacher_bp.route('/panel')
@login_required
@role_required('teacher')
def panel():
    """Панель преподавателя"""
    user = get_user_by_id(session['user_id'])
    profile = get_profile_by_user(user)
    actions = get_available_actions(user)
    
    # Получаем группы преподавателя
    groups = []
    if profile:
        groups = get_teacher_groups(profile.teacher_id)
    
    return render_template('teacher/panel.html',
                         user=user,
                         profile=profile,
                         actions=actions,
                         groups=groups)

@teacher_bp.route('/group/<int:group_id>')
@login_required
@role_required('teacher')
def group_detail(group_id):
    """Просмотр группы"""
    user = get_user_by_id(session['user_id'])
    profile = get_profile_by_user(user)
    
    if not has_permission(user, 'students', 'read'):
        flash('У вас нет прав для просмотра студентов', 'error')
        return redirect(url_for('teacher.panel'))
    
    students = get_group_students(group_id)
    
    return render_template('teacher/group_detail.html',
                         user=user,
                         profile=profile,
                         students=students,
                         group_id=group_id)