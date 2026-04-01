import sqlite3
import os

DB_PATH = 'instance/university.db'

def view_table(cursor, table_name):
    print(f"\n{'='*50}")
    print(f"ТАБЛИЦА: {table_name}")
    print('='*50)
    
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 20")
    rows = cursor.fetchall()
    
    if not rows:
        print("  (пусто)")
        return
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    
    print(" | ".join(columns))
    print("-" * 50)
    
    for row in rows:
        print(" | ".join(str(v) for v in row))

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Список всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t[0] for t in cursor.fetchall() if not t[0].startswith('sqlite_')]
    
    print("Доступные таблицы:")
    for t in tables:
        print(f"  - {t}")
    
    for table in tables:
        view_table(cursor, table)
    
    conn.close()

if __name__ == '__main__':
    main()