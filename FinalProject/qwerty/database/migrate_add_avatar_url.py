"""Migration: Add avatar_url column to users and riders tables.
Idempotent: checks existence before adding.
"""
import os
import sqlite3

try:
    import pymysql
except ImportError:
    pymysql = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

def column_exists_sqlite(cur, table, col):
    cur.execute(f"PRAGMA table_info('{table}')")
    return any(r[1] == col for r in cur.fetchall())

def column_exists_mysql(cur, table, col):
    cur.execute(f"SHOW COLUMNS FROM {table} LIKE '{col}'")
    return cur.fetchone() is not None

def add_avatar_url_columns():
    if DB_ENGINE == 'mysql':
        conn = pymysql.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASS', ''),
            db=os.environ.get('DB_NAME', 'qwerty'),
            port=int(os.environ.get('DB_PORT', '3306')),
            cursorclass=pymysql.cursors.Cursor,
            charset='utf8mb4'
        )
        cur = conn.cursor()
        
        # Add avatar_url to users table
        if not column_exists_mysql(cur, 'users', 'avatar_url'):
            cur.execute("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) NULL")
            print(f"[mysql] Added avatar_url column to users table")
        else:
            print(f"[mysql] avatar_url column already exists in users table")
        
        # Add avatar_url to riders table
        if not column_exists_mysql(cur, 'riders', 'avatar_url'):
            cur.execute("ALTER TABLE riders ADD COLUMN avatar_url VARCHAR(500) NULL")
            print(f"[mysql] Added avatar_url column to riders table")
        else:
            print(f"[mysql] avatar_url column already exists in riders table")
        
        conn.commit()
        conn.close()
        print('Avatar URL column migration complete!')
    else:  # SQLite
        db_path = os.path.join(BASE_DIR, 'qwerty.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Add avatar_url to users table
        if not column_exists_sqlite(cur, 'users', 'avatar_url'):
            cur.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
            print(f"[sqlite] Added avatar_url column to users table")
        else:
            print(f"[sqlite] avatar_url column already exists in users table")
        
        # Add avatar_url to riders table
        if not column_exists_sqlite(cur, 'riders', 'avatar_url'):
            cur.execute("ALTER TABLE riders ADD COLUMN avatar_url TEXT")
            print(f"[sqlite] Added avatar_url column to riders table")
        else:
            print(f"[sqlite] avatar_url column already exists in riders table")
        
        conn.commit()
        conn.close()
        print('Avatar URL column migration complete!')

if __name__ == '__main__':
    add_avatar_url_columns()

