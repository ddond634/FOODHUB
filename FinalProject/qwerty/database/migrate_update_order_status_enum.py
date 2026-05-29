"""
Migration Script: Update Order Status ENUM/CHECK Constraint
Updates the orders.status column to include all status values used by the application:
'placed', 'pending', 'processing', 'ready', 'dispatched', 'in-transit', 'shipped', 'delivered', 'completed', 'cancelled'

This fixes the issue where status updates to 'ready', 'pending', etc. were being rejected by the database.
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

# All valid status values used by the application
ALL_STATUSES = ['placed', 'pending', 'processing', 'ready', 'dispatched', 'in-transit', 'shipped', 'delivered', 'completed', 'cancelled']

def migrate_mysql():
    """Update MySQL ENUM to include all status values"""
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
        
        # Check current ENUM values
        print("🔍 Checking current status column definition...")
        cursor.execute("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'orders' 
            AND COLUMN_NAME = 'status'
        """, (db_config['database'],))
        
        result = cursor.fetchone()
        if not result:
            print("❌ Status column not found in orders table!")
            cursor.close()
            connection.close()
            return False
        
        current_enum = result['COLUMN_TYPE']
        print(f"   Current ENUM: {current_enum}\n")
        
        # Build new ENUM string
        enum_values = "','".join(ALL_STATUSES)
        new_enum = f"ENUM('{enum_values}')"
        
        if current_enum.upper() == new_enum.upper():
            print("⚠️  Status ENUM already contains all required values. No migration needed.")
            cursor.close()
            connection.close()
            return True
        
        print("🔄 Updating status ENUM to include all status values...")
        print(f"   New ENUM: {new_enum}\n")
        
        # Modify the column to include all status values
        # Note: MODIFY COLUMN will preserve existing data
        cursor.execute(f"""
            ALTER TABLE orders 
            MODIFY COLUMN status {new_enum} DEFAULT 'placed'
        """)
        
        print("   ✅ Status ENUM updated successfully\n")
        
        # Verify the update
        cursor.execute("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'orders' 
            AND COLUMN_NAME = 'status'
        """, (db_config['database'],))
        
        verify_result = cursor.fetchone()
        updated_enum = verify_result['COLUMN_TYPE']
        print(f"   Verified ENUM: {updated_enum}\n")
        
        # Commit changes
        connection.commit()
        print("✅ Migration completed successfully!")
        print("\n📊 Summary:")
        print(f"   - Updated orders.status ENUM to include {len(ALL_STATUSES)} status values")
        print(f"   - All status values: {', '.join(ALL_STATUSES)}")
        
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
    """Update SQLite CHECK constraint to include all status values"""
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
        
        # SQLite doesn't support modifying CHECK constraints directly
        # We need to recreate the table
        print("🔍 Checking current table structure...")
        
        # Get current table schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'")
        result = cursor.fetchone()
        if not result:
            print("❌ Orders table not found!")
            cursor.close()
            conn.close()
            return False
        
        old_sql = result['sql']
        print(f"   Current table definition found\n")
        
        # Check if the CHECK constraint already includes all statuses
        if all(status in old_sql for status in ALL_STATUSES):
            print("⚠️  Status CHECK constraint already contains all required values. No migration needed.")
            cursor.close()
            conn.close()
            return True
        
        print("🔄 Updating status CHECK constraint...")
        print("   Note: SQLite requires table recreation to modify CHECK constraints\n")
        
        # Build new CHECK constraint
        status_list = "','".join(ALL_STATUSES)
        check_constraint = f"CHECK(status IN ('{status_list}'))"
        
        # Step 1: Create new table with updated constraint
        print("1️⃣  Creating temporary table with updated CHECK constraint...")
        cursor.execute(f"""
            CREATE TABLE orders_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                customer_name TEXT,
                customer_phone TEXT,
                customer_address TEXT,
                subtotal REAL,
                delivery_fee REAL,
                total REAL,
                payment TEXT,
                status TEXT {check_constraint} DEFAULT 'placed',
                rider_id INTEGER,
                created_at TEXT,
                delivered_at TEXT,
                FOREIGN KEY(rider_id) REFERENCES riders(id) ON DELETE SET NULL
            )
        """)
        print("   ✅ Temporary table created\n")
        
        # Step 2: Copy data from old table to new table
        print("2️⃣  Copying data from old table to new table...")
        cursor.execute("""
            INSERT INTO orders_new 
            (id, customer_id, customer_name, customer_phone, customer_address, 
             subtotal, delivery_fee, total, payment, status, rider_id, created_at, delivered_at)
            SELECT 
                id, customer_id, customer_name, customer_phone, customer_address,
                subtotal, delivery_fee, total, payment, 
                CASE 
                    WHEN status IS NULL OR status = '' THEN 'placed'
                    ELSE status
                END as status,
                rider_id, created_at, delivered_at
            FROM orders
        """)
        rows_copied = cursor.rowcount
        print(f"   ✅ Copied {rows_copied} row(s)\n")
        
        # Step 3: Drop old table
        print("3️⃣  Dropping old table...")
        cursor.execute("DROP TABLE orders")
        print("   ✅ Old table dropped\n")
        
        # Step 4: Rename new table
        print("4️⃣  Renaming new table...")
        cursor.execute("ALTER TABLE orders_new RENAME TO orders")
        print("   ✅ Table renamed\n")
        
        # Step 5: Recreate indexes if they existed
        print("5️⃣  Recreating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_rider_id ON orders(rider_id)")
        print("   ✅ Indexes recreated\n")
        
        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        print("\n📊 Summary:")
        print(f"   - Updated orders.status CHECK constraint to include {len(ALL_STATUSES)} status values")
        print(f"   - All status values: {', '.join(ALL_STATUSES)}")
        print(f"   - Migrated {rows_copied} order(s)")
        
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
    print("🚀 Order Status ENUM/CHECK Constraint Migration Script")
    print("=" * 70)
    print()
    print(f"Database Engine: {DB_ENGINE.upper()}")
    print(f"Status values to add: {', '.join(ALL_STATUSES)}")
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
        print("   2. Test updating an order status to 'ready' or 'pending'")
        print("   3. Verify the status persists after refresh")
    else:
        print("❌ Migration process failed. Please check the errors above.")
    print("=" * 70)

if __name__ == "__main__":
    main()

