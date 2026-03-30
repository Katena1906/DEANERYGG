from flask import Flask, render_template, request, redirect, url_for, session, abort
from functools import wraps
from database.db import init_db, db
from database.models import User, Student, Teacher, Faculty
from services.auth_service import authenticate, get_user_by_id, get_profile_by_user
from services.authz_service import has_permission, get_available_actions, get_role_info


app = Flask(__name__)
init_db(app)



def login_required(f):
    """Проверка: пользователь должен быть авторизован"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Проверка: у пользователя должна быть одна из указанных ролей"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            user = get_user_by_id(session['user_id'])
            if not user or user.role not in roles:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(permission):
    """Проверка: у пользователя должно быть указанное право"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            user = get_user_by_id(session['user_id'])
            if not user or not has_permission(user, permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# МАРШРУТЫ


@app.route('/')
def index():
    """Корневой маршрут — перенаправление на логин или дашборд"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Проверяем, есть ли пользователь
        from services.auth_service import identify_user, is_account_locked
        user_check = identify_user(email)
        
        # Если пользователь существует и заблокирован — показываем сообщение
        if user_check and is_account_locked(user_check):
            error = 'Аккаунт заблокирован на 5 минут. Слишком много неудачных попыток.'
        else:
            user = authenticate(email, password)
            if user:
                session['user_id'] = user.user_id
                session['user_role'] = user.role
                return redirect(url_for('dashboard'))
            else:
                # Если пользователь существует, считаем попытки
                if user_check:
                    attempts_left = 3 - (user_check.failed_attempts or 0)
                    if attempts_left > 0:
                        error = f'Неверный email или пароль. Осталось попыток: {attempts_left}'
                    else:
                        error = 'Аккаунт заблокирован на 5 минут. Слишком много неудачных попыток.'
                else:
                    error = 'Неверный email или пароль'
    
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Главная страница после входа — перенаправление по роли"""
    user = get_user_by_id(session['user_id'])
    
    if user.role == 'student':
        return redirect(url_for('student_panel'))
    elif user.role == 'teacher':
        return redirect(url_for('teacher_panel'))
    elif user.role == 'dean':
        return redirect(url_for('dean_panel'))
    elif user.role == 'admin':
        return redirect(url_for('admin_panel'))
    
    return render_template('dashboard.html', user=user)


@app.route('/student_panel')
@login_required
@role_required('student')
def student_panel():
    """Панель студента"""
    user = get_user_by_id(session['user_id'])
    profile = get_profile_by_user(user)
    actions = get_available_actions(user)
    
    return render_template('student_panel.html', 
                          user=user, 
                          profile=profile, 
                          actions=actions)


@app.route('/teacher_panel')
@login_required
@role_required('teacher')
def teacher_panel():
    """Панель преподавателя"""
    user = get_user_by_id(session['user_id'])
    profile = get_profile_by_user(user)
    actions = get_available_actions(user)
    
    return render_template('teacher_panel.html', 
                          user=user, 
                          profile=profile, 
                          actions=actions)


@app.route('/dean_panel')
@login_required
@role_required('dean')
def dean_panel():
    """Панель деканата"""
    user = get_user_by_id(session['user_id'])
    profile = get_profile_by_user(user)
    actions = get_available_actions(user)
    
    return render_template('dean_panel.html', 
                          user=user, 
                          profile=profile, 
                          actions=actions)


@app.route('/admin_panel')
@login_required
@role_required('admin')
def admin_panel():
    """Панель администратора"""
    user = get_user_by_id(session['user_id'])
    actions = get_available_actions(user)
    
    # Получаем статистику
    from database.models import User, Student, Teacher, Faculty
    
    stats = {
        'users_count': User.query.count(),
        'students_count': Student.query.count(),
        'teachers_count': Teacher.query.count(),
        'faculties_count': Faculty.query.count()
    }
    
    return render_template('admin_panel.html', 
                          user=user, 
                          actions=actions,
                          stats=stats)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)