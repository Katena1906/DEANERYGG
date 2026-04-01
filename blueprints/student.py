# blueprints/student.py
from flask import Blueprint, render_template, session, redirect, url_for, flash
from decorators.auth import login_required, role_required
from services.auth_service import get_user_by_id, get_profile_by_user
from services.authz_service import get_available_actions
from database.models import Grade, AcademicDebt, Discipline, AssessmentType
from services.data_service import get_student_grades, get_student_debts

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/panel')
@login_required
@role_required('student')
def panel():
    """Панель студента"""
    user = get_user_by_id(session['user_id'])
    profile = get_profile_by_user(user)
    actions = get_available_actions(user)
    
    # Получаем последние оценки студента
    recent_grades = []
    if profile:
        recent_grades = get_student_grades(profile.student_id, limit=5)
    
    # Получаем активные долги
    active_debts = []
    if profile:
        active_debts = get_student_debts(profile.student_id, active_only=True)
    
    return render_template('student/panel.html',
                         user=user,
                         profile=profile,
                         actions=actions,
                         recent_grades=recent_grades,
                         active_debts=active_debts)