# decorators/permissions.py
from functools import wraps
from flask import session, redirect, url_for, abort, flash
from services.auth_service import get_user_by_id
from services.authz_service import has_permission

def permission_required(resource, action):
    """
    Декоратор: проверяет, что у пользователя есть указанное право.
    
    Использование:
        @permission_required('grades', 'create')
        def create_grade():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Пожалуйста, войдите в систему', 'warning')
                return redirect(url_for('auth.login_page'))
            
            user = get_user_by_id(session['user_id'])
            if not user or not has_permission(user, resource, action):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator