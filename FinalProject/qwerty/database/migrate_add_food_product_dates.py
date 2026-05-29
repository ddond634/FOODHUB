"""
Migration: Add manufacture_date and expiry_date columns to products table
For food and beverage products tracking
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def migrate():
    if DB_ENGINE == 'mysql':
        conn = pymysql.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASS', ''),
            db=os.environ.get('DB_NAME', 'qwerty'),
            port=int(os.environ.get('DB_PORT', '3306')),
            cursorclass=pymysql.cursors.DictCursor
        )
    else:
        import sqlite3
        conn = sqlite3.connect('qwerty.db')
        conn.row_factory = sqlite3.Row
    
    cur = conn.cursor()
    
    try:
        print("[MIGRATION] Adding manufacture_date and expiry_date columns to products table...")
        
        # Check if columns already exist
        if DB_ENGINE == 'mysql':
            cur.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'products' AND COLUMN_NAME = 'manufacture_date'
            """, (os.environ.get('DB_NAME', 'qwerty'),))
            result = cur.fetchone()
            manufacture_exists = result['cnt'] > 0
            
            cur.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'products' AND COLUMN_NAME = 'expiry_date'
            """, (os.environ.get('DB_NAME', 'qwerty'),))
            result = cur.fetchone()
            expiry_exists = result['cnt'] > 0
        else:
            cur.execute("PRAGMA table_info('products')")
            cols = cur.fetchall()
            col_names = [col[1] if isinstance(col, tuple) else col['name'] for col in cols]
            manufacture_exists = 'manufacture_date' in col_names
            expiry_exists = 'expiry_date' in col_names
        
        # Add manufacture_date if it doesn't exist
        if not manufacture_exists:
            if DB_ENGINE == 'mysql':
                cur.execute("""
                    ALTER TABLE products 
                    ADD COLUMN manufacture_date DATE NULL
                """)
            else:
                cur.execute("""
                    ALTER TABLE products 
                    ADD COLUMN manufacture_date TEXT NULL
                """)
            print("✅ Added manufacture_date column")
        else:
            print("⏭️  manufacture_date column already exists")
        
        # Add expiry_date if it doesn't exist
        if not expiry_exists:
            if DB_ENGINE == 'mysql':
                cur.execute("""
                    ALTER TABLE products 
                    ADD COLUMN expiry_date DATE NULL
                """)
            else:
                cur.execute("""
                    ALTER TABLE products 
                    ADD COLUMN expiry_date TEXT NULL
                """)
            print("✅ Added expiry_date column")
        else:
            print("⏭️  expiry_date column already exists")
        
        conn.commit()
        print("[SUCCESS] Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    migrate()
