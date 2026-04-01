# blueprints/dean.py
from flask import Blueprint, render_template, session, redirect, url_for, flash
from decorators.auth import login_required, role_required
from services.auth_service import get_user_by_id, get_profile_by_user
from services.authz_service import get_available_actions
from services.data_service import get_faculty_groups, get_faculty_stats
from database.models import Student, AcademicDebt
from database.db import db

dean_bp = Blueprint('dean', __name__, url_prefix='/dean')

@dean_bp.route('/panel')
@login_required
@role_required('dean')
def panel():
    """Панель деканата"""
    user = get_user_by_id(session['user_id'])
    profile = get_profile_by_user(user)
    actions = get_available_actions(user)
    
    # Статистика факультета
    stats = {}
    if profile:
        stats = get_faculty_stats(profile.faculty_id)
        groups = get_faculty_groups(profile.faculty_id)
    else:
        groups = []
    
    return render_template('dean/panel.html',
                         user=user,
                         profile=profile,
                         actions=actions,
                         stats=stats,
                         groups=groups)