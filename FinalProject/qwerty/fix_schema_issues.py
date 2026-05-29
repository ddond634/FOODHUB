"""
Migration: Add missing cart_items table and update wishlist schema
Run this to fix database schema issues
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'db': os.environ.get('DB_NAME', 'qwerty'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'charset': 'utf8mb4'
}

def run_migration():
    print("=" * 60)
    print("DATABASE SCHEMA FIX MIGRATION")
    print("=" * 60)
    
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cur = conn.cursor()
        
        # 1. Add cart_items table
        print("\n[1/3] Creating cart_items table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL DEFAULT 1,
                price_total DECIMAL(12,2),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_product (user_id, product_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                INDEX idx_user (user_id)
            ) ENGINE=InnoDB;
        """)
        print("✓ cart_items table created")
        
        # 2. Check if wishlist columns exist, add if missing
        print("\n[2/3] Checking wishlist table schema...")
        cur.execute("SHOW COLUMNS FROM wishlist LIKE 'quantity'")
        if not cur.fetchone():
            print("  Adding quantity column to wishlist...")
            cur.execute("ALTER TABLE wishlist ADD COLUMN quantity INT NOT NULL DEFAULT 1 AFTER product_id")
            print("  ✓ quantity column added")
        else:
            print("  ✓ quantity column already exists")
        
        cur.execute("SHOW COLUMNS FROM wishlist LIKE 'price_total'")
        if not cur.fetchone():
            print("  Adding price_total column to wishlist...")
            cur.execute("ALTER TABLE wishlist ADD COLUMN price_total DECIMAL(12,2) AFTER quantity")
            print("  ✓ price_total column added")
        else:
            print("  ✓ price_total column already exists")
        
        # 3. Add performance indexes
        print("\n[3/3] Adding performance indexes...")
        
        indexes = [
            ("users", "idx_email", "email"),
            ("users", "idx_role", "role"),
            ("products", "idx_seller", "seller_id"),
            ("products", "idx_category", "category"),
            ("orders", "idx_customer", "customer_id"),
            ("orders", "idx_status", "status"),
            ("orders", "idx_created", "created_at"),
            ("order_items", "idx_product", "product_id"),
        ]
        
        for table, index_name, column in indexes:
            try:
                # Check if index exists
                cur.execute(f"SHOW INDEX FROM {table} WHERE Key_name = '{index_name}'")
                if not cur.fetchone():
                    cur.execute(f"CREATE INDEX {index_name} ON {table}({column})")
                    print(f"  ✓ Added index {index_name} on {table}({column})")
                else:
                    print(f"  - Index {index_name} already exists")
            except Exception as e:
                print(f"  ⚠ Could not add index {index_name}: {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nChanges applied:")
        print("  - cart_items table created")
        print("  - wishlist.quantity column added")
        print("  - wishlist.price_total column added")
        print("  - Performance indexes added")
        print("\nServer can now handle cart and wishlist operations.")
        
    except Exception as e:
        print(f"\n✗ MIGRATION FAILED: {e}")
        print("\nPlease check:")
        print("  1. MySQL is running")
        print("  2. Database credentials in .env are correct")
        print("  3. Database 'qwerty' exists")
        return False
    
    return True

if __name__ == '__main__':
    success = run_migration()
    exit(0 if success else 1)
