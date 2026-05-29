"""
Migration: Add shop_status column to sellers table

This migration adds:
- shop_status ENUM('pending','active','suspended') DEFAULT 'pending'
- approved_at DATETIME

Run this if you have an existing database.
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# MySQL configuration
MYSQL_HOST = os.environ.get('DB_HOST', '127.0.0.1')
MYSQL_USER = os.environ.get('DB_USER', 'root')
MYSQL_PASS = os.environ.get('DB_PASS', '')
MYSQL_DB = os.environ.get('DB_NAME', 'qwerty')
MYSQL_PORT = int(os.environ.get('DB_PORT', '3306'))

def migrate():
    """Add shop_status and approved_at columns to sellers table"""
    print("=" * 60)
    print("  Migration: Add shop_status to sellers table")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASS,
            db=MYSQL_DB,
            port=MYSQL_PORT,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        print("\nChecking if migration is needed...")
        
        # Check if column already exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'sellers' 
            AND COLUMN_NAME = 'shop_status'
        """, (MYSQL_DB,))
        
        if cursor.fetchone():
            print("✓ Column 'shop_status' already exists. Migration not needed.")
            cursor.close()
            conn.close()
            return True
        
        print("\nAdding shop_status column...")
        
        # Add shop_status column
        cursor.execute("""
            ALTER TABLE sellers 
            ADD COLUMN shop_status ENUM('pending','active','suspended') DEFAULT 'pending' 
            AFTER verified
        """)
        
        # Add approved_at column
        cursor.execute("""
            ALTER TABLE sellers 
            ADD COLUMN approved_at DATETIME AFTER shop_status
        """)
        
        # Update existing verified sellers to have active shop status
        cursor.execute("""
            UPDATE sellers 
            SET shop_status = 'active', 
                approved_at = NOW() 
            WHERE verified = 1
        """)
        
        affected_rows = cursor.rowcount
        
        conn.commit()
        
        print("✓ Column 'shop_status' added successfully")
        print("✓ Column 'approved_at' added successfully")
        print(f"✓ Updated {affected_rows} existing verified seller(s) to 'active' status")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        
        return True
        
    except pymysql.Error as e:
        print(f"\n✗ Migration failed: {e}")
        return False

if __name__ == '__main__':
    try:
        success = migrate()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        exit(1)
