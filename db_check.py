import sqlite3
import os
import sys
from database_manager import DATABASE_NAME, init_db

def check_tables():
    if not os.path.exists(DATABASE_NAME):
        print(f"Il database '{DATABASE_NAME}' non esiste.")

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Get existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    required_tables = ['users', 'transactions']
    missing_tables = [table for table in required_tables if table not in existing_tables]

    if missing_tables:
        print(f"Le seguenti tabelle sono mancanti: {', '.join(missing_tables)}")
        choice = input("Vuoi creare le tabelle mancanti ora? (s/n): ").lower()
        if choice == 's':
            init_db()
            print("Tabelle create con successo.")
        else:
            print("Avvio annullato. Le tabelle sono necessarie per il funzionamento.")
            sys.exit(1)
    else:
        print("Tutte le tabelle sono presenti.")

if __name__ == "__main__":
    check_tables()
