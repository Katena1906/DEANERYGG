# blueprints/dashboard.py
from flask import Blueprint, redirect, url_for, session, render_template
from services.auth_service import get_user_by_id
from decorators.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Главная страница дашборда с редиректом на соответствующую панель"""
    user = get_user_by_id(session['user_id'])
    
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    # Маршрутизация на соответствующие панели
    role_routes = {
        'student': 'student.panel',
        'teacher': 'teacher.panel',
        'dean': 'dean.panel',
        'admin': 'admin.panel'
    }
    
    if user.role in role_routes:
        return redirect(url_for(role_routes[user.role]))
    
    # Если роль не определена, выходим
    session.clear()
    return redirect(url_for('auth.login'))