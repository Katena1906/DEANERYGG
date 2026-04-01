#deanery/database/db.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """Инициализация базы данных"""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///university.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
    db.init_app(app)
    
    with app.app_context():
        db.create_all()