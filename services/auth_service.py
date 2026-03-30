
import bcrypt
from datetime import datetime, timedelta
from database.db import db
from database.models import User

MAX_ATTEMPTS = 3
LOCK_TIME = timedelta(minutes=5)


def validate_password(password: str) -> bool:
    return (
        len(password) >= 6 and
        any(c.isdigit() for c in password) 
    )


def hash_password(password: str) -> str:
    if not validate_password(password):
        raise ValueError("Пароль не соответствует требованиям безопасности")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def identify_user(email: str):
    return User.query.filter_by(email=email).first()


def is_account_locked(user: User) -> bool:
    if user.failed_attempts >= MAX_ATTEMPTS:
        if user.last_failed:
            if datetime.utcnow() - user.last_failed < LOCK_TIME:
                return True
    return False


def authenticate(email: str, password: str):
    user = identify_user(email)
    if not user:
        return None

    if is_account_locked(user):
        return None

    if not verify_password(password, user.password_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        user.last_failed = datetime.utcnow()
        db.session.commit()
        return None

    # успешный вход
    user.failed_attempts = 0
    user.last_login = datetime.utcnow()
    db.session.commit()
    return user


def get_user_by_id(user_id: int):
    return User.query.get(user_id)


def get_profile_by_user(user):
    from database.models import Student, Teacher, Faculty
    if user.role == 'student' and user.related_id:
        return Student.query.get(user.related_id)
    elif user.role == 'teacher' and user.related_id:
        return Teacher.query.get(user.related_id)
    elif user.role == 'dean' and user.related_id:
        return Faculty.query.get(user.related_id)
    return None