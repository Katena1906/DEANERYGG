# blueprints/admin.py
from flask import Blueprint, render_template, session, redirect, url_for, flash
from decorators.auth import login_required, role_required
from services.auth_service import get_user_by_id
from services.authz_service import get_available_actions
from services.data_service import get_system_statistics

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/panel')
@login_required
@role_required('admin')
def panel():
    """Панель администратора"""
    user = get_user_by_id(session['user_id'])
    actions = get_available_actions(user)
    
    # Получаем статистику системы
    stats = get_system_statistics()
    
    return render_template('admin/panel.html',
                         user=user,
                         actions=actions,
                         stats=stats)