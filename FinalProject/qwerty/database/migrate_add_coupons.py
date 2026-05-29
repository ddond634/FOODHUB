"""
Migration: Add Coupons System
Creates coupons table for store coupons issued as refunds
"""
import pymysql
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite')
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'db': os.environ.get('DB_NAME', 'qwerty'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'charset': 'utf8mb4'
}

def run_migration():
    """Execute the migration"""
    try:
        print(f"\n=== Coupons System Migration ({DB_ENGINE.upper()}) ===\n")
        
        if DB_ENGINE == 'mysql':
            conn = pymysql.connect(**DB_CONFIG)
        else:
            conn = sqlite3.connect('qwerty.db')
        
        cursor = conn.cursor()
        
        # Create coupons table
        print("1. Creating coupons table...")
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coupons (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    customer_id INT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    used_amount DECIMAL(10,2) DEFAULT 0.00,
                    status VARCHAR(20) DEFAULT 'active',
                    issued_for VARCHAR(100),
                    return_refund_request_id INT,
                    expires_at DATETIME NULL,
                    used_at DATETIME NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (return_refund_request_id) REFERENCES return_refund_requests(id) ON DELETE SET NULL,
                    INDEX idx_code (code),
                    INDEX idx_customer (customer_id),
                    INDEX idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coupons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    customer_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    used_amount REAL DEFAULT 0.00,
                    status TEXT DEFAULT 'active',
                    issued_for TEXT,
                    return_refund_request_id INTEGER,
                    expires_at DATETIME NULL,
                    used_at DATETIME NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (return_refund_request_id) REFERENCES return_refund_requests(id) ON DELETE SET NULL
                )
            """)
        print("   ✅ coupons table created")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Migration completed successfully!\n")
        print("Tables created:")
        print("  - coupons: Store coupon codes issued as refunds\n")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}\n")
        raise

if __name__ == '__main__':
    run_migration()

