# decorators/auth.py
from functools import wraps
from flask import session, redirect, url_for, abort, flash
from services.auth_service import get_user_by_id

def login_required(f):
    """Декоратор: требует авторизации пользователя"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('auth.login_page'))
        
        # Проверяем, что пользователь существует
        user = get_user_by_id(session['user_id'])
        if not user:
            session.clear()
            flash('Сессия недействительна, пожалуйста, войдите снова', 'warning')
            return redirect(url_for('auth.login_page'))
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Декоратор: требует наличия одной из указанных ролей"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Пожалуйста, войдите в систему', 'warning')
                return redirect(url_for('auth.login_page'))
            
            user = get_user_by_id(session['user_id'])
            if not user or user.role not in roles:
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator