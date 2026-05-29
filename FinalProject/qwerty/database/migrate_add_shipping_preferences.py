"""
Migration: Add shipping preferences to sellers
Adds free_shipping_threshold and standard_shipping_fee columns
"""

import os
import sys
import pymysql

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def get_connection():
    """Get database connection without Flask context"""
    if DB_ENGINE == 'mysql':
        return pymysql.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', ''),
            database=os.environ.get('DB_NAME', 'qwerty'),
            port=int(os.environ.get('DB_PORT', 3306))
        )
    else:
        import sqlite3
        return sqlite3.connect('qwerty.db')

def migrate():
    """Add shipping preference columns to sellers table"""
    print("🔄 Starting migration: Add Shipping Preferences")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if DB_ENGINE == 'mysql':
            print("📝 Adding shipping preference columns to sellers table...")
            
            # Check if columns already exist
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'sellers' 
                AND COLUMN_NAME = 'free_shipping_threshold'
            """)
            
            if cursor.fetchone()[0] == 0:
                # Add free_shipping_threshold column
                cursor.execute("""
                    ALTER TABLE sellers 
                    ADD COLUMN free_shipping_threshold DECIMAL(10,2) DEFAULT 500.00
                    COMMENT 'Minimum order amount for free shipping'
                """)
                print("✅ Added free_shipping_threshold column")
            else:
                print("ℹ️  free_shipping_threshold column already exists")
            
            # Check if standard_shipping_fee exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'sellers' 
                AND COLUMN_NAME = 'standard_shipping_fee'
            """)
            
            if cursor.fetchone()[0] == 0:
                # Add standard_shipping_fee column
                cursor.execute("""
                    ALTER TABLE sellers 
                    ADD COLUMN standard_shipping_fee DECIMAL(10,2) DEFAULT 50.00
                    COMMENT 'Shipping fee per item when below threshold'
                """)
                print("✅ Added standard_shipping_fee column")
            else:
                print("ℹ️  standard_shipping_fee column already exists")
            
        else:  # SQLite
            print("📝 Adding shipping preference columns to sellers table...")
            
            # SQLite doesn't support ADD COLUMN IF NOT EXISTS, so we need to check
            cursor.execute("PRAGMA table_info(sellers)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'free_shipping_threshold' not in columns:
                cursor.execute("""
                    ALTER TABLE sellers 
                    ADD COLUMN free_shipping_threshold DECIMAL(10,2) DEFAULT 500.00
                """)
                print("✅ Added free_shipping_threshold column")
            else:
                print("ℹ️  free_shipping_threshold column already exists")
            
            if 'standard_shipping_fee' not in columns:
                cursor.execute("""
                    ALTER TABLE sellers 
                    ADD COLUMN standard_shipping_fee DECIMAL(10,2) DEFAULT 50.00
                """)
                print("✅ Added standard_shipping_fee column")
            else:
                print("ℹ️  standard_shipping_fee column already exists")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        print("\nDefault values set:")
        print("  - Free shipping threshold: ₱500.00")
        print("  - Standard shipping fee: ₱50.00 per item")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
