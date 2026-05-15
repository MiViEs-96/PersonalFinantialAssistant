import sqlite3
from datetime import datetime

DATABASE_NAME = 'finance_assistant.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            nickname TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            last_access DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def add_user(full_name, nickname, hashed_password):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (full_name, nickname, password) VALUES (?, ?, ?)',
                     (full_name, nickname, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_nickname(nickname):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE nickname = ?', (nickname,)).fetchone()
    conn.close()
    return user

def get_user_by_full_name(full_name):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE full_name = ?', (full_name,)).fetchone()
    conn.close()
    return user

def update_last_access(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET last_access = ? WHERE id = ?', (datetime.now(), user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db_connection()
    users = conn.execute('SELECT full_name, nickname, last_access FROM users').fetchall()
    conn.close()
    return users

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
