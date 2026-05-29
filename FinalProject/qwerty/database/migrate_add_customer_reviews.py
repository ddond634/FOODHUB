"""
Migration: Add Customer Reviews System
Creates the reviews table for customer feedback on products and sellers
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', ''),
    'database': os.getenv('DB_NAME', 'qwerty'),
    'port': int(os.getenv('DB_PORT', '3306'))
}

def migrate():
    """Add reviews table to database"""
    print("🔄 Starting migration: Add Customer Reviews System")
    
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Create reviews table
        print("📝 Creating reviews table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                order_id INT NOT NULL,
                product_id INT NOT NULL,
                seller_id INT NOT NULL,
                rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT,
                images TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_customer (customer_id),
                INDEX idx_product (product_id),
                INDEX idx_seller (seller_id),
                INDEX idx_order (order_id),
                INDEX idx_rating (rating),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB
        ''')
        
        conn.commit()
        print("✅ Reviews table created successfully")
        
        cursor.close()
        conn.close()
        
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == '__main__':
    migrate()
