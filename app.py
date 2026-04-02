
# app.py
from flask import Flask,  render_template
from flask_cors import CORS
from database.db import init_db, db
import os
from dotenv import load_dotenv

load_dotenv()

def create_app(config_override=None):
    app = Flask(__name__)
    
    # Базовая конфигурация
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 
        'sqlite:///deanery.db'  # Для разработки используем SQLite
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Переопределение конфигурации для тестов
    if config_override:
        app.config.update(config_override)
    
    # CORS настройки
    CORS(app, supports_credentials=True)
    
    # Инициализация БД
    init_db(app)
    
    # Регистрация blueprints
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.student import student_bp
    from blueprints.teacher import teacher_bp
    from blueprints.dean import dean_bp
    from blueprints.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(dean_bp)
    app.register_blueprint(admin_bp)
    
    # Обработчики ошибок
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
#Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
