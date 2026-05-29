#!/usr/bin/env python3
"""
Fix notifications table - add missing columns
"""
import pymysql
import sqlite3
import sys
import os

def run_mysql():
    """Fix MySQL notifications table"""
    try:
        print("\n=== MySQL: Fixing notifications table ===\n")
        
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='qwerty',
            charset='utf8mb4'
        )
        cur = conn.cursor()
        
        # Check if type column exists
        cur.execute("SHOW COLUMNS FROM notifications LIKE 'type'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE notifications ADD COLUMN type VARCHAR(50) DEFAULT 'general' AFTER `read`")
            print("✓ Added type column to notifications table")
        else:
            print("→ type column already exists")
        
        # Check if related_id column exists
        cur.execute("SHOW COLUMNS FROM notifications LIKE 'related_id'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE notifications ADD COLUMN related_id INT NULL AFTER type")
            print("✓ Added related_id column to notifications table")
        else:
            print("→ related_id column already exists")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("\n✅ MySQL migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def run_sqlite():
    """Fix SQLite notifications table"""
    try:
        print("\n=== SQLite: Fixing notifications table ===\n")
        
        conn = sqlite3.connect('qwerty.db')
        cur = conn.cursor()
        
        # Check if type column exists
        cur.execute("PRAGMA table_info(notifications)")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'type' not in columns:
            cur.execute("ALTER TABLE notifications ADD COLUMN type TEXT DEFAULT 'general'")
            print("✓ Added type column to notifications table")
        else:
            print("→ type column already exists")
        
        if 'related_id' not in columns:
            cur.execute("ALTER TABLE notifications ADD COLUMN related_id INTEGER")
            print("✓ Added related_id column to notifications table")
        else:
            print("→ related_id column already exists")
        
        conn.commit()
        conn.close()
        
        print("\n✅ SQLite migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix notifications table')
    parser.add_argument('--db', choices=['sqlite', 'mysql'], default='mysql',
                       help='Database type (default: mysql)')
    args = parser.parse_args()
    
    if args.db == 'sqlite':
        success = run_sqlite()
    else:
        success = run_mysql()
    
    sys.exit(0 if success else 1)
