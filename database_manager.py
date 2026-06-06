import sqlite3
from datetime import datetime

DATABASE_NAME = 'finance_assistant.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            nickname TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            last_access DATETIME
        )
    ''')

    # Create transactions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            direction TEXT NOT NULL, -- 'entrata' or 'uscita'
            category TEXT NOT NULL,  -- e.g., 'cibo', 'stipendio'
            nickname TEXT NOT NULL,
            comment TEXT,
            FOREIGN KEY (nickname) REFERENCES users(nickname)
        )
    ''')
    conn.commit()
    conn.close()

# --- User Management ---

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

# --- Transaction Management ---

def add_transaction(date, amount, currency, direction, category, nickname, comment):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO transactions (date, amount, currency, direction, category, nickname, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (date, amount, currency, direction, category, nickname, comment))
    conn.commit()
    conn.close()

def get_transactions_by_user(nickname):
    conn = get_db_connection()
    transactions = conn.execute('''
        SELECT * FROM transactions WHERE nickname = ? ORDER BY date DESC, id DESC
    ''', (nickname,)).fetchall()
    conn.close()
    return transactions

def get_stats_data(nickname, start_date=None, end_date=None):
    conn = get_db_connection()
    query = 'SELECT * FROM transactions WHERE nickname = ?'
    params = [nickname]

    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)

    data = conn.execute(query, params).fetchall()
    conn.close()
    return data

def get_paginated_transactions(nickname, page=1, per_page=10, start_date=None, end_date=None, direction=None, category=None):
    conn = get_db_connection()
    query = 'FROM transactions WHERE nickname = ?'
    params = [nickname]

    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    if direction:
        query += ' AND direction = ?'
        params.append(direction)
    if category:
        query += ' AND category = ?'
        params.append(category)

    # Get total count
    count_query = 'SELECT COUNT(*) ' + query
    total_count = conn.execute(count_query, params).fetchone()[0]

    # Get data
    data_query = 'SELECT * ' + query + ' ORDER BY date DESC, id DESC LIMIT ? OFFSET ?'
    data_params = params + [per_page, (page - 1) * per_page]
    transactions = conn.execute(data_query, data_params).fetchall()

    conn.close()
    return transactions, total_count

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
