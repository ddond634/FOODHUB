"""
Migration script to add messaging features:
- Add attachment_url and attachment_type columns to messages table
- Add greeting_message column to sellers table
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def migrate_mysql():
    """Migrate MySQL database"""
    import pymysql
    
    config = {
        'host': os.environ.get('DB_HOST', '127.0.0.1'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASS', ''),
        'db': os.environ.get('DB_NAME', 'qwerty'),
        'port': int(os.environ.get('DB_PORT', '3306')),
        'charset': 'utf8mb4'
    }
    
    print(f"Connecting to MySQL: {config['db']}@{config['host']}:{config['port']}")
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    try:
        # Check if attachment columns exist in messages table
        cursor.execute("""
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'messages' AND COLUMN_NAME = 'attachment_url'
        """, (config['db'],))
        
        if cursor.fetchone()[0] == 0:
            print("Adding attachment_url column to messages table...")
            cursor.execute("ALTER TABLE messages ADD COLUMN attachment_url VARCHAR(512) NULL AFTER message")
            print("✓ Added attachment_url column")
        else:
            print("⏭️  attachment_url column already exists")
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'messages' AND COLUMN_NAME = 'attachment_type'
        """, (config['db'],))
        
        if cursor.fetchone()[0] == 0:
            print("Adding attachment_type column to messages table...")
            cursor.execute("ALTER TABLE messages ADD COLUMN attachment_type VARCHAR(100) NULL AFTER attachment_url")
            print("✓ Added attachment_type column")
        else:
            print("⏭️  attachment_type column already exists")
        
        # Check if greeting_message exists in sellers table
        cursor.execute("""
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'sellers' AND COLUMN_NAME = 'greeting_message'
        """, (config['db'],))
        
        if cursor.fetchone()[0] == 0:
            print("Adding greeting_message column to sellers table...")
            cursor.execute("ALTER TABLE sellers ADD COLUMN greeting_message TEXT NULL")
            print("✓ Added greeting_message column")
        else:
            print("⏭️  greeting_message column already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        conn.close()

def migrate_sqlite():
    """Migrate SQLite database"""
    import sqlite3
    
    db_path = os.path.join(BASE_DIR, 'qwerty.db')
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return
    
    print(f"Connecting to SQLite: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if attachment columns exist in messages table
        cursor.execute("PRAGMA table_info(messages)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        if 'attachment_url' not in existing_cols:
            print("Adding attachment_url column to messages table...")
            cursor.execute("ALTER TABLE messages ADD COLUMN attachment_url TEXT NULL")
            print("✓ Added attachment_url column")
        else:
            print("⏭️  attachment_url column already exists")
        
        if 'attachment_type' not in existing_cols:
            print("Adding attachment_type column to messages table...")
            cursor.execute("ALTER TABLE messages ADD COLUMN attachment_type TEXT NULL")
            print("✓ Added attachment_type column")
        else:
            print("⏭️  attachment_type column already exists")
        
        # Check if greeting_message exists in sellers table
        cursor.execute("PRAGMA table_info(sellers)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        if 'greeting_message' not in existing_cols:
            print("Adding greeting_message column to sellers table...")
            cursor.execute("ALTER TABLE sellers ADD COLUMN greeting_message TEXT NULL")
            print("✓ Added greeting_message column")
        else:
            print("⏭️  greeting_message column already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("Messaging Features Migration")
    print("=" * 60)
    print(f"Database Engine: {DB_ENGINE}\n")
    
    if DB_ENGINE == 'mysql':
        migrate_mysql()
    else:
        migrate_sqlite()
    
    print("\n" + "=" * 60)
    print("Migration script completed!")
    print("=" * 60)

