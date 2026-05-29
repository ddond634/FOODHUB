"""
Migration Script: Add rider_id Column to Orders Table
Adds the rider_id column to the orders table if it doesn't exist.
This column is used to track which rider is assigned to deliver an order.
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
    """Add rider_id column to orders table in MySQL"""
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
        
        # Check if rider_id column already exists
        print("🔍 Checking if rider_id column exists in orders table...")
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'orders' 
            AND COLUMN_NAME = 'rider_id'
        """, (db_config['database'],))
        
        if cursor.fetchone():
            print("⚠️  rider_id column already exists. No migration needed.")
            cursor.close()
            connection.close()
            return True
        
        print("🔄 Adding rider_id column to orders table...")
        
        # Check if riders table exists first
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'riders'
        """, (db_config['database'],))
        
        riders_table_exists = cursor.fetchone() is not None
        
        if riders_table_exists:
            # Add rider_id column with foreign key constraint
            cursor.execute("""
                ALTER TABLE orders 
                ADD COLUMN rider_id INT NULL,
                ADD CONSTRAINT fk_orders_rider 
                FOREIGN KEY (rider_id) REFERENCES riders(id) ON DELETE SET NULL
            """)
            print("   ✅ rider_id column added with foreign key constraint\n")
        else:
            # Add rider_id column without foreign key (riders table doesn't exist yet)
            cursor.execute("""
                ALTER TABLE orders 
                ADD COLUMN rider_id INT NULL
            """)
            print("   ✅ rider_id column added (no foreign key - riders table doesn't exist)\n")
        
        # Commit changes
        connection.commit()
        print("✅ Migration completed successfully!")
        print("\n📊 Summary:")
        print("   - Added rider_id column to orders table")
        print("   - Column allows NULL values (for unassigned orders)")
        if riders_table_exists:
            print("   - Foreign key constraint added to riders table")
        
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
    """Add rider_id column to orders table in SQLite"""
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
        
        # Check if rider_id column already exists
        print("🔍 Checking if rider_id column exists in orders table...")
        cursor.execute("PRAGMA table_info(orders)")
        columns = cursor.fetchall()
        
        column_names = [col[1] if isinstance(col, tuple) else col['name'] for col in columns]
        
        if 'rider_id' in column_names:
            print("⚠️  rider_id column already exists. No migration needed.")
            cursor.close()
            conn.close()
            return True
        
        print("🔄 Adding rider_id column to orders table...")
        
        # SQLite doesn't support adding foreign keys to existing tables easily
        # We'll just add the column without the foreign key constraint
        cursor.execute("""
            ALTER TABLE orders 
            ADD COLUMN rider_id INTEGER
        """)
        print("   ✅ rider_id column added\n")
        
        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        print("\n📊 Summary:")
        print("   - Added rider_id column to orders table")
        print("   - Column allows NULL values (for unassigned orders)")
        print("   - Note: SQLite foreign key constraints require table recreation")
        
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
    print("🚀 Add rider_id Column to Orders Table Migration Script")
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
        print("   2. Test accepting an order in the Rider Dashboard")
        print("   3. Verify the order is assigned to the rider")
    else:
        print("❌ Migration process failed. Please check the errors above.")
    print("=" * 70)

if __name__ == "__main__":
    main()

