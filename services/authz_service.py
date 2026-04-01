# services/authz_service.py
from database.models import User

# Права доступа для каждой роли
ROLE_PERMISSIONS = {
    'student': {
        'grades': ['read_own'],
        'debts': ['read_own'],
        'deadlines': ['read_own'],
        'schedule': ['read_own'],
        'notifications': ['read_own']
    },
    'teacher': {
        'grades': ['create', 'read'],
        'debts': ['read'],
        'deadlines': ['create', 'read'],
        'students': ['read'],
        'schedule': ['read']
    },
    'dean': {
        'students': ['read_all'],
        'grades': ['read_all'],
        'debts': ['manage'],
        'deadlines': ['manage'],
        'events': ['create', 'read'],
        'reports': ['generate'],
        'schedule': ['create']
    },
    'admin': {
        'users': ['create', 'read', 'update', 'delete'],
        'roles': ['manage'],
        'statistics': ['read'],
        'system': ['full_access']
    }
}

ACTION_NAMES = {
    # Студент (5 действий)
    ('grades', 'read_own'): 'Мои оценки',
    ('debts', 'read_own'): 'Мои долги',
    ('deadlines', 'read_own'): 'Мои дедлайны',
    ('schedule', 'read_own'): 'Расписание',
    ('notifications', 'read_own'): 'Уведомления',
    
    # Преподаватель (6 действий)
    ('grades', 'create'): 'Выставить оценки',
    ('grades', 'read'): 'Просмотр оценок',
    ('deadlines', 'create'): 'Создать дедлайн',
    ('deadlines', 'read'): 'Контроль дедлайнов',
    ('students', 'read'): 'Студенты',
    
    # Деканат (6 действий)
    ('students', 'read_all'): 'Все студенты',
    ('grades', 'read_all'): 'Успеваемость',
    ('debts', 'manage'): 'Управление долгами',
    ('deadlines', 'manage'): 'Контроль дедлайнов',
    ('events', 'create'): 'Планирование',
    ('reports', 'generate'): 'Отчеты',
    
    # Администратор (4 действия)
    ('users', 'create'): 'Управление пользователями',
    ('users', 'read'): 'Список пользователей',
    ('roles', 'manage'): 'Управление ролями',
    ('statistics', 'read'): 'Статистика системы'
}

def has_permission(user: User, resource: str, action: str) -> bool:
    """Проверка наличия права у пользователя"""
    if not user:
        return False
    if user.role == 'admin':
        return True
    perms = ROLE_PERMISSIONS.get(user.role, {})
    return resource in perms and action in perms[resource]

def get_available_actions(user: User) -> list:
    """Получение списка доступных действий для пользователя"""
    if not user:
        return []
    
    actions = []
    
    if user.role == 'student':
        actions = ['Мои оценки', 'Мои долги', 'Мои дедлайны', 'Расписание', 'Уведомления']
    elif user.role == 'teacher':
        actions = ['Выставить оценки', 'Просмотр оценок', 'Создать дедлайн', 
                   'Контроль дедлайнов', 'Студенты']
    elif user.role == 'dean':
        actions = ['Все студенты', 'Успеваемость', 'Управление долгами', 
                   'Контроль дедлайнов', 'Планирование', 'Отчеты']
    elif user.role == 'admin':
        actions = ['Управление пользователями', 'Список пользователей', 
                   'Управление ролями', 'Статистика системы']
    
    return actions

def get_action_name(resource: str, action: str) -> str:
    """Получение человекочитаемого названия действия"""
    return ACTION_NAMES.get((resource, action), f"{resource}.{action}")