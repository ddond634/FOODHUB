"""Quick script to add phone column to users and riders tables if missing."""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

def add_phone_columns():
    """Add phone column to users and riders tables if they don't exist."""
    if DB_ENGINE == 'mysql':
        import pymysql
        conn = pymysql.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASS', ''),
            db=os.environ.get('DB_NAME', 'qwerty'),
            port=int(os.environ.get('DB_PORT', '3306')),
            charset='utf8mb4'
        )
    else:
        import sqlite3
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'qwerty.db'))
    
    cur = conn.cursor()
    
    try:
        if DB_ENGINE == 'mysql':
            # Check and add to users table
            cur.execute("SHOW COLUMNS FROM users LIKE 'phone'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(255) NULL")
                print("[mysql] Added phone column to users table")
            else:
                print("[mysql] phone column already exists in users table")
            
            # Check and add to riders table
            cur.execute("SHOW COLUMNS FROM riders LIKE 'phone'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE riders ADD COLUMN phone VARCHAR(255) NULL")
                print("[mysql] Added phone column to riders table")
            else:
                print("[mysql] phone column already exists in riders table")
        else:
            # SQLite
            import sqlite3
            cur.execute("PRAGMA table_info(users)")
            users_cols = [row[1] for row in cur.fetchall()]
            if 'phone' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")
                print("[sqlite] Added phone column to users table")
            else:
                print("[sqlite] phone column already exists in users table")
            
            cur.execute("PRAGMA table_info(riders)")
            riders_cols = [row[1] for row in cur.fetchall()]
            if 'phone' not in riders_cols:
                cur.execute("ALTER TABLE riders ADD COLUMN phone TEXT")
                print("[sqlite] Added phone column to riders table")
            else:
                print("[sqlite] phone column already exists in riders table")
        
        conn.commit()
        print("Phone column migration complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    add_phone_columns()

