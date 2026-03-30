
from database.models import User

ROLE_PERMISSIONS = {
    'student': {
        'grades': ['read_own'],
        'schedule': ['read'],
        'debts': ['read_own'],
        'retakes': ['read_own'],
        'notifications': ['read']
    },
    'teacher': {
        'groups': ['read'],
        'students': ['read'],
        'grades': ['create', 'update'],
        'retakes': ['read', 'create']
    },
    'dean': {
        'students': ['read_all'],
        'grades': ['read_all'],
        'debts': ['read_all', 'manage'],
        'retakes': ['read_all', 'manage'],
        'reports': ['generate'],
        'statistics': ['read']
    },
    'admin': {
        'users': ['create', 'read', 'update', 'delete'],
        'roles': ['manage'],
        'faculty': ['manage'],
        'system': ['full_access']
    }
}


def has_permission(user: User, resource: str, action: str) -> bool:
    if not user:
        return False
    role_perms = ROLE_PERMISSIONS.get(user.role, {})
    if resource not in role_perms:
        return False
    return action in role_perms[resource]


def get_user_permissions(user: User) -> dict:
    if not user:
        return {}
    return ROLE_PERMISSIONS.get(user.role, {})


def get_available_actions(user: User) -> list:
    permissions = get_user_permissions(user)
    actions = []
    
    # Человекочитаемые названия для каждого действия
    action_names = {
        ('grades', 'read_own'): 'Мои оценки',
        ('grades', 'read_all'): 'Все оценки',
        ('grades', 'create'): 'Выставить оценку',
        ('grades', 'update'): 'Изменить оценку',
        ('schedule', 'read'): 'Расписание',
        ('debts', 'read_own'): 'Мои долги',
        ('debts', 'read_all'): 'Все долги',
        ('debts', 'manage'): 'Управление долгами',
        ('retakes', 'read_own'): 'Мои пересдачи',
        ('retakes', 'read_all'): 'Все пересдачи',
        ('retakes', 'create'): 'Назначить пересдачу',
        ('retakes', 'read'): 'Просмотреть пересдачи',
        ('retakes', 'manage'): 'Управление пересдачами',
        ('notifications', 'read'): 'Уведомления',
        ('groups', 'read'): 'Мои группы',
        ('students', 'read'): 'Студенты группы',
        ('students', 'read_all'): 'Все студенты',
        ('reports', 'generate'): 'Сформировать отчёты',
        ('statistics', 'read'): 'Статистика',
        ('users', 'create'): 'Создать пользователя',
        ('users', 'read'): 'Список пользователей',
        ('users', 'update'): 'Редактировать пользователя',
        ('users', 'delete'): 'Удалить пользователя',
        ('roles', 'manage'): 'Управление ролями',
        ('faculty', 'manage'): 'Управление факультетами',
        ('system', 'full_access'): 'Полный доступ к системе'
    }
    
    for resource, acts in permissions.items():
        for act in acts:
            key = (resource, act)
            if key in action_names:
                actions.append(action_names[key])
            else:
                actions.append(f"{resource}:{act}")
    
    return actions


def get_role_info(user: User) -> dict:
    if not user:
        return {}
    permissions = get_user_permissions(user)
    return {
        'role': user.role,
        'resources_count': len(permissions),
        'permissions': permissions
    }