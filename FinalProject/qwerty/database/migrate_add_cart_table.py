"""
Migration: Add cart_items table
This migration adds a cart_items table for shopping cart functionality.
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    """Add cart_items table to MySQL database"""
    
    # Connect to MySQL
    connection = pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', ''),
        database=os.getenv('DB_NAME', 'qwerty'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with connection.cursor() as cursor:
            print("Creating cart_items table...")
            
            # Create cart_items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cart_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    product_id INT NOT NULL,
                    variation_id INT DEFAULT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_cart_item (user_id, product_id, variation_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            
            connection.commit()
            print("✅ Successfully created cart_items table")
            
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'cart_items'")
            result = cursor.fetchone()
            if result:
                print("✅ Verified: cart_items table exists")
                
                # Show table structure
                cursor.execute("DESCRIBE cart_items")
                columns = cursor.fetchall()
                print("\nTable structure:")
                for col in columns:
                    print(f"  - {col['Field']}: {col['Type']}")
            else:
                print("❌ Error: cart_items table not found after creation")
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        connection.rollback()
        raise
    finally:
        connection.close()

if __name__ == '__main__':
    migrate()
