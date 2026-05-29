"""Add cart_items table to MySQL database"""
import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'qwerty_fresh',
    'charset': 'utf8mb4'
}

def add_cart_table():
    """Add cart_items table"""
    try:
        print("🔧 Connecting to MySQL...")
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("📋 Creating cart_items table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_product (user_id, product_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
        """)
        conn.commit()
        
        # Verify table was created
        cursor.execute("SHOW TABLES LIKE 'cart_items'")
        if cursor.fetchone():
            print("✅ cart_items table created successfully!")
        else:
            print("❌ Failed to create cart_items table")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("  Add cart_items table")
    print("=" * 60)
    print()
    add_cart_table()
