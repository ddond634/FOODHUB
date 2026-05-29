"""
Migration: Add last_login column to users table
Stores the timestamp of the user's most recent login
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def migrate():
    try:
        if DB_ENGINE == 'mysql':
            import pymysql
            conn = pymysql.connect(
                host=os.environ.get('DB_HOST', '127.0.0.1'),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASS', ''),
                db=os.environ.get('DB_NAME', 'qwerty'),
                port=int(os.environ.get('DB_PORT', '3306'))
            )
            cursor = conn.cursor()
            
            print("🔧 Adding last_login column to users table...")
            
            # Check if column exists
            cursor.execute("SHOW COLUMNS FROM users LIKE 'last_login'")
            if cursor.fetchone():
                print("  ⚠️  Column last_login already exists, skipping...")
            else:
                cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME NULL")
                conn.commit()
                print("  ✅ last_login column added successfully")
            
        else:
            import sqlite3
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(BASE_DIR, 'qwerty.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            print("🔧 Adding last_login column to users table...")
            
            # Check if column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'last_login' in columns:
                print("  ⚠️  Column last_login already exists, skipping...")
            else:
                cursor.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
                conn.commit()
                print("  ✅ last_login column added successfully")
        
        cursor.close()
        conn.close()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate()

