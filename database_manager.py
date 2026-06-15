import sqlite3
from datetime import datetime

DATABASE_NAME = 'finance_assistant.db'
INVESTMENT_KEYWORDS = ['investment', 'investimento', '投资']

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

    # Create user_balances table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            month TEXT NOT NULL, -- YYYY-MM format
            balance REAL NOT NULL,
            UNIQUE(nickname, month),
            FOREIGN KEY (nickname) REFERENCES users(nickname)
        )
    ''')

    # Create investment_summaries table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS investment_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            month TEXT NOT NULL, -- YYYY-MM format
            invested REAL DEFAULT 0,
            withdrawn REAL DEFAULT 0,
            UNIQUE(nickname, month),
            FOREIGN KEY (nickname) REFERENCES users(nickname)
        )
    ''')

    conn.commit()

    # Migration: Populate investment_summaries from existing transactions ONLY if table is empty
    count = conn.execute("SELECT COUNT(*) FROM investment_summaries").fetchone()[0]
    if count == 0:
        transactions = conn.execute("SELECT nickname, date, amount, direction, category FROM transactions").fetchall()
        for t in transactions:
            if t['category'].lower() in INVESTMENT_KEYWORDS:
                month = t['date'][:7]
                if t['direction'] == 'uscita':
                    conn.execute('''
                        INSERT INTO investment_summaries (nickname, month, invested) VALUES (?, ?, ?)
                        ON CONFLICT(nickname, month) DO UPDATE SET invested = invested + excluded.invested
                    ''', (t['nickname'], month, t['amount']))
                else:
                    conn.execute('''
                        INSERT INTO investment_summaries (nickname, month, withdrawn) VALUES (?, ?, ?)
                        ON CONFLICT(nickname, month) DO UPDATE SET withdrawn = withdrawn + excluded.withdrawn
                    ''', (t['nickname'], month, t['amount']))
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

def update_user_profile(user_id, old_nickname, new_full_name, new_nickname):
    conn = get_db_connection()
    try:
        # 1. Update user record
        conn.execute('UPDATE users SET full_name = ?, nickname = ? WHERE id = ?',
                     (new_full_name, new_nickname, user_id))

        # 2. Update all related tables if nickname changed
        if old_nickname != new_nickname:
            conn.execute('UPDATE transactions SET nickname = ? WHERE nickname = ?',
                         (new_nickname, old_nickname))
            conn.execute('UPDATE user_balances SET nickname = ? WHERE nickname = ?',
                         (new_nickname, old_nickname))
            conn.execute('UPDATE investment_summaries SET nickname = ? WHERE nickname = ?',
                         (new_nickname, old_nickname))

        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# --- Balance & Investment Management ---

def set_user_balance(nickname, month, balance):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO user_balances (nickname, month, balance)
            VALUES (?, ?, ?)
            ON CONFLICT(nickname, month) DO UPDATE SET balance=excluded.balance
        ''', (nickname, month, balance))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_user_balance(nickname, month):
    conn = get_db_connection()
    row = conn.execute('SELECT balance FROM user_balances WHERE nickname = ? AND month = ?',
                       (nickname, month)).fetchone()
    conn.close()
    return row['balance'] if row else None

def get_all_user_balances(nickname):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM user_balances WHERE nickname = ? ORDER BY month ASC',
                        (nickname,)).fetchall()
    conn.close()
    return rows

def get_user_first_balance_month(nickname):
    conn = get_db_connection()
    row = conn.execute('SELECT month FROM user_balances WHERE nickname = ? ORDER BY month ASC LIMIT 1',
                       (nickname,)).fetchone()
    conn.close()
    return row['month'] if row else None

def update_investment_summary(nickname, month, amount, direction):
    # direction: 'entrata' (withdrawn) or 'uscita' (invested)
    conn = get_db_connection()
    try:
        if direction == 'uscita':
            conn.execute('''
                INSERT INTO investment_summaries (nickname, month, invested) VALUES (?, ?, ?)
                ON CONFLICT(nickname, month) DO UPDATE SET invested = invested + excluded.invested
            ''', (nickname, month, amount))
        else:
            conn.execute('''
                INSERT INTO investment_summaries (nickname, month, withdrawn) VALUES (?, ?, ?)
                ON CONFLICT(nickname, month) DO UPDATE SET withdrawn = withdrawn + excluded.withdrawn
            ''', (nickname, month, amount))
        conn.commit()
    finally:
        conn.close()

def get_investment_summaries(nickname):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM investment_summaries WHERE nickname = ? ORDER BY month ASC',
                        (nickname,)).fetchall()
    conn.close()
    return rows

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

def get_category_usage_counts():
    conn = get_db_connection()
    counts = conn.execute('''
        SELECT category, direction, COUNT(*) as count
        FROM transactions
        GROUP BY category, direction
    ''').fetchall()
    conn.close()

    # Format as a dict: {(category, direction): count}
    result = {}
    for row in counts:
        result[(row['category'], row['direction'])] = row['count']
    return result

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
