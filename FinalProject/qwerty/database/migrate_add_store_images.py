"""
Migration: Add store logo and banner columns to sellers table
"""

import pymysql.cursors
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    """Add store_logo and store_banner columns to sellers table"""
    
    connection = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DB', 'qwerty'),
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with connection.cursor() as cursor:
            # Check if columns already exist
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'sellers' 
                AND COLUMN_NAME IN ('store_logo', 'store_banner', 'store_name', 'store_description')
            """, (os.getenv('MYSQL_DB', 'qwerty'),))
            
            existing_columns = {row['COLUMN_NAME'] for row in cursor.fetchall()}
            
            # Add store_name if it doesn't exist
            if 'store_name' not in existing_columns:
                print("Adding store_name column...")
                cursor.execute("""
                    ALTER TABLE sellers 
                    ADD COLUMN store_name VARCHAR(255) AFTER business_name
                """)
                print("✓ Added store_name column")
            else:
                print("✓ store_name column already exists")
            
            # Add store_description if it doesn't exist
            if 'store_description' not in existing_columns:
                print("Adding store_description column...")
                cursor.execute("""
                    ALTER TABLE sellers 
                    ADD COLUMN store_description TEXT AFTER store_name
                """)
                print("✓ Added store_description column")
            else:
                print("✓ store_description column already exists")
            
            # Add store_logo if it doesn't exist
            if 'store_logo' not in existing_columns:
                print("Adding store_logo column...")
                cursor.execute("""
                    ALTER TABLE sellers 
                    ADD COLUMN store_logo VARCHAR(768) AFTER store_description
                """)
                print("✓ Added store_logo column")
            else:
                print("✓ store_logo column already exists")
            
            # Add store_banner if it doesn't exist
            if 'store_banner' not in existing_columns:
                print("Adding store_banner column...")
                cursor.execute("""
                    ALTER TABLE sellers 
                    ADD COLUMN store_banner VARCHAR(768) AFTER store_logo
                """)
                print("✓ Added store_banner column")
            else:
                print("✓ store_banner column already exists")
            
            connection.commit()
            print("\n✅ Migration completed successfully!")
            
    except Exception as e:
        connection.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        connection.close()

if __name__ == '__main__':
    migrate()
