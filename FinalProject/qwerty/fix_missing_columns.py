#!/usr/bin/env python3
"""
Database Schema Fix: Missing columns for sellers and notifications
- Adds declined_at, declined_by, decline_reason to sellers table
- Adds type, message, action_url to notifications table
"""
import pymysql
import sys

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'qwerty',
    'charset': 'utf8mb4'
}

def column_exists(cur, table, column):
    """Check if a column exists in a table"""
    cur.execute("""
        SELECT COUNT(*) 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = 'qwerty' 
        AND TABLE_NAME = %s 
        AND COLUMN_NAME = %s
    """, (table, column))
    return cur.fetchone()[0] > 0

def run_migration():
    """Execute database schema updates"""
    try:
        print("\n=== Starting Schema Migration (Sellers + Notifications) ===\n")
        
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Phase 1: Add columns to sellers table
        print("[1/2] Updating sellers table...")
        
        columns_to_add = [
            ('declined_at', 'DATETIME'),
            ('declined_by', 'INT'),
            ('decline_reason', 'TEXT')
        ]
        
        for col_name, col_type in columns_to_add:
            if not column_exists(cur, 'sellers', col_name):
                print(f"    Adding {col_name} column...")
                if col_name == 'declined_by':
                    cur.execute(f"""
                        ALTER TABLE sellers 
                        ADD COLUMN {col_name} {col_type},
                        ADD FOREIGN KEY (declined_by) REFERENCES users(id) ON DELETE SET NULL
                    """)
                else:
                    cur.execute(f"ALTER TABLE sellers ADD COLUMN {col_name} {col_type}")
                conn.commit()
                print(f"    ✓ {col_name} added")
            else:
                print(f"    ⚠ {col_name} already exists, skipping")
        
        # Phase 2: Add columns to notifications table
        print("[2/2] Updating notifications table...")
        
        notifications_columns = [
            ('type', "VARCHAR(50) DEFAULT 'general'"),
            ('message', 'TEXT'),
            ('action_url', 'VARCHAR(512)')
        ]
        
        for col_name, col_type in notifications_columns:
            if not column_exists(cur, 'notifications', col_name):
                print(f"    Adding {col_name} column...")
                cur.execute(f"ALTER TABLE notifications ADD COLUMN {col_name} {col_type}")
                conn.commit()
                print(f"    ✓ {col_name} added")
            else:
                print(f"    ⚠ {col_name} already exists, skipping")
        
        cur.close()
        conn.close()
        
        print("\n=== Migration Complete ===")
        print("✓ Sellers table updated (declined_at, declined_by, decline_reason)")
        print("✓ Notifications table updated (type, message, action_url)")
        print("\nNext: Restart server to use new schema\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
