"""
Migration Script: Add delivered_at Column to Orders Table
Adds the delivered_at column to the orders table if it doesn't exist.
This column tracks when an order was delivered.
"""

import os
import sys
import sqlite3
from dotenv import load_dotenv

# Add parent directory to path to import backend modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

load_dotenv()

DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

def migrate_mysql():
    """Add delivered_at column to orders table in MySQL"""
    try:
        import pymysql
    except ImportError:
        print("❌ pymysql not installed. Cannot migrate MySQL database.")
        return False
    
    db_config = {
        'host': os.getenv('DB_HOST', '127.0.0.1'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASS', ''),
        'database': os.getenv('DB_NAME', 'qwerty'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    
    try:
        print("Connecting to MySQL database...")
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        print("✅ Connected successfully!\n")
        
        # Check if delivered_at column already exists
        print("🔍 Checking if delivered_at column exists in orders table...")
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'orders' 
            AND COLUMN_NAME = 'delivered_at'
        """, (db_config['database'],))
        
        if cursor.fetchone():
            print("⚠️  delivered_at column already exists. No migration needed.")
            cursor.close()
            connection.close()
            return True
        
        print("🔄 Adding delivered_at column to orders table...")
        
        # Add delivered_at column (allows NULL for orders not yet delivered)
        cursor.execute("""
            ALTER TABLE orders 
            ADD COLUMN delivered_at DATETIME NULL
            AFTER created_at
        """)
        print("   ✅ delivered_at column added\n")
        
        # Commit changes
        connection.commit()
        print("✅ Migration completed successfully!")
        print("\n📊 Summary:")
        print("   - Added delivered_at column to orders table")
        print("   - Column allows NULL values (for undelivered orders)")
        print("   - Column type: DATETIME")
        
        cursor.close()
        connection.close()
        print("\n✅ Database connection closed")
        return True
        
    except pymysql.Error as e:
        print(f"\n❌ MySQL Error: {e}")
        if 'connection' in locals():
            connection.rollback()
            connection.close()
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if 'connection' in locals():
            connection.rollback()
            connection.close()
        return False

def migrate_sqlite():
    """Add delivered_at column to orders table in SQLite"""
    db_path = os.path.join(BASE_DIR, 'qwerty.db')
    
    if not os.path.exists(db_path):
        print(f"❌ SQLite database not found at: {db_path}")
        return False
    
    try:
        print(f"Connecting to SQLite database: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        print("✅ Connected successfully!\n")
        
        # Check if delivered_at column already exists
        print("🔍 Checking if delivered_at column exists in orders table...")
        cursor.execute("PRAGMA table_info(orders)")
        columns = cursor.fetchall()
        
        column_names = [col[1] if isinstance(col, tuple) else col['name'] for col in columns]
        
        if 'delivered_at' in column_names:
            print("⚠️  delivered_at column already exists. No migration needed.")
            cursor.close()
            conn.close()
            return True
        
        print("🔄 Adding delivered_at column to orders table...")
        
        # Add delivered_at column (allows NULL for orders not yet delivered)
        cursor.execute("""
            ALTER TABLE orders 
            ADD COLUMN delivered_at TEXT
        """)
        print("   ✅ delivered_at column added\n")
        
        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        print("\n📊 Summary:")
        print("   - Added delivered_at column to orders table")
        print("   - Column allows NULL values (for undelivered orders)")
        print("   - Column type: TEXT (SQLite)")
        
        cursor.close()
        conn.close()
        print("\n✅ Database connection closed")
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ SQLite Error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    print("=" * 70)
    print("🚀 Add delivered_at Column to Orders Table Migration Script")
    print("=" * 70)
    print()
    print(f"Database Engine: {DB_ENGINE.upper()}")
    print()
    
    success = False
    if DB_ENGINE == 'mysql':
        success = migrate_mysql()
    else:
        success = migrate_sqlite()
    
    print()
    print("=" * 70)
    if success:
        print("🎉 Migration process completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Restart your Flask application")
        print("   2. Test marking an order as delivered in the Rider Dashboard")
        print("   3. Verify the delivered_at timestamp is recorded")
    else:
        print("❌ Migration process failed. Please check the errors above.")
    print("=" * 70)

if __name__ == "__main__":
    main()

