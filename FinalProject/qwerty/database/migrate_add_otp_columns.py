#!/usr/bin/env python3
"""
Migration script to add otp_code and is_verified columns to users table.
Run this if you have an existing database that needs the new columns.
"""

import os
import sys
import pymysql
import sqlite3
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()
DB_PATH = os.path.join(BASE_DIR, 'qwerty.db')

MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'db': os.environ.get('DB_NAME', 'qwerty'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'charset': 'utf8mb4',
    'autocommit': False
}


def migrate_mysql():
    """Add OTP columns to MySQL database."""
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cur = conn.cursor()
        
        print("[MYSQL] Checking for otp_code column...")
        cur.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME='users' AND COLUMN_NAME='otp_code'
        """)
        
        if cur.fetchone()[0] == 0:
            print("[MYSQL] Adding otp_code column...")
            cur.execute("ALTER TABLE users ADD COLUMN otp_code VARCHAR(6) DEFAULT NULL;")
            print("[MYSQL] ✓ Added otp_code column")
        else:
            print("[MYSQL] otp_code column already exists")
        
        print("[MYSQL] Checking for is_verified column...")
        cur.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME='users' AND COLUMN_NAME='is_verified'
        """)
        
        if cur.fetchone()[0] == 0:
            print("[MYSQL] Adding is_verified column...")
            cur.execute("ALTER TABLE users ADD COLUMN is_verified TINYINT DEFAULT 0;")
            print("[MYSQL] ✓ Added is_verified column")
        else:
            print("[MYSQL] is_verified column already exists")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("[MYSQL] Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"[MYSQL ERROR] {str(e)}")
        return False


def migrate_sqlite():
    """Add OTP columns to SQLite database."""
    try:
        if not os.path.exists(DB_PATH):
            print(f"[SQLITE] Database not found at {DB_PATH}")
            return False
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Check if columns exist
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        
        if 'otp_code' not in columns:
            print("[SQLITE] Adding otp_code column...")
            cur.execute("ALTER TABLE users ADD COLUMN otp_code TEXT DEFAULT NULL;")
            print("[SQLITE] ✓ Added otp_code column")
        else:
            print("[SQLITE] otp_code column already exists")
        
        if 'is_verified' not in columns:
            print("[SQLITE] Adding is_verified column...")
            cur.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0;")
            print("[SQLITE] ✓ Added is_verified column")
        else:
            print("[SQLITE] is_verified column already exists")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("[SQLITE] Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"[SQLITE ERROR] {str(e)}")
        return False


def main():
    print("=" * 60)
    print("Hub E-Commerce - OTP Columns Migration")
    print("=" * 60)
    
    if DB_ENGINE == 'mysql':
        print(f"\n[INFO] Migrating MySQL database: {MYSQL_CONFIG['db']}")
        success = migrate_mysql()
    else:
        print(f"\n[INFO] Migrating SQLite database: {DB_PATH}")
        success = migrate_sqlite()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Start the server: python 'py files/run_server.py'")
        print("2. Test registration and OTP verification flows")
        print("=" * 60)
        return 0
    else:
        print("✗ Migration failed. Check errors above.")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
