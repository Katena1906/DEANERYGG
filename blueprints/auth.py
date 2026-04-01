# blueprints/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.auth_service import authenticate, identify_user, is_account_locked
from decorators.auth import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    # Если уже авторизован, перенаправляем на дашборд
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    
    error = None
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            error = 'Пожалуйста, заполните все поля'
        else:
            user_check = identify_user(email)
            
            if user_check and is_account_locked(user_check):
                error = 'Аккаунт заблокирован на 5 минут. Слишком много неудачных попыток.'
            else:
                user = authenticate(email, password)
                if user:
                    session['user_id'] = user.user_id
                    session['user_role'] = user.role
                    flash(f'Добро пожаловать, {user.email}!', 'success')
                    return redirect(url_for('dashboard.index'))
                else:
                    if user_check:
                        attempts_left = 3 - (user_check.failed_attempts or 0)
                        if attempts_left > 0:
                            error = f'Неверный email или пароль. Осталось попыток: {attempts_left}'
                        else:
                            error = 'Аккаунт заблокирован на 5 минут.'
                    else:
                        error = 'Неверный email или пароль'
    
    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/login-page')
def login_page():
    """Алиас для страницы входа (используется в декораторах)"""
    return redirect(url_for('auth.login'))