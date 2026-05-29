"""
Migration: Add Product Sales/Discount System
Creates tables and logic for expiring product sales with seller/admin approval workflow
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
        print(f"\n=== Product Sales System Migration ({DB_ENGINE.upper()}) ===\n")
        
        if DB_ENGINE == 'mysql':
            conn = pymysql.connect(**DB_CONFIG)
        else:
            conn = sqlite3.connect('qwerty.db')
        
        cursor = conn.cursor()
        
        # 1. Create product_sales table
        print("1. Creating product_sales table...")
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_sales (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    discount_percentage DECIMAL(5,2) NOT NULL DEFAULT 0.00,
                    original_price DECIMAL(10,2) NOT NULL,
                    sale_price DECIMAL(10,2) NOT NULL,
                    reason VARCHAR(50) DEFAULT 'expiring_soon',
                    status VARCHAR(20) DEFAULT 'pending',
                    days_until_expiry INT,
                    seller_profit_margin DECIMAL(5,2),
                    platform_commission DECIMAL(5,2) DEFAULT 7.50,
                    seller_requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_approved_at DATETIME NULL,
                    admin_rejected_at DATETIME NULL,
                    valid_from DATETIME DEFAULT CURRENT_TIMESTAMP,
                    valid_until DATETIME NULL,
                    requested_by INT,
                    approved_by INT NULL,
                    admin_notes TEXT,
                    is_active BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                    FOREIGN KEY (requested_by) REFERENCES users(id),
                    FOREIGN KEY (approved_by) REFERENCES users(id),
                    INDEX idx_product_sale (product_id, is_active),
                    INDEX idx_status (status),
                    INDEX idx_expiry (days_until_expiry)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    discount_percentage REAL NOT NULL DEFAULT 0.00,
                    original_price REAL NOT NULL,
                    sale_price REAL NOT NULL,
                    reason TEXT DEFAULT 'expiring_soon',
                    status TEXT DEFAULT 'pending',
                    days_until_expiry INTEGER,
                    seller_profit_margin REAL,
                    platform_commission REAL DEFAULT 7.50,
                    seller_requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_approved_at DATETIME NULL,
                    admin_rejected_at DATETIME NULL,
                    valid_from DATETIME DEFAULT CURRENT_TIMESTAMP,
                    valid_until DATETIME NULL,
                    requested_by INTEGER,
                    approved_by INTEGER NULL,
                    admin_notes TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                    FOREIGN KEY (requested_by) REFERENCES users(id),
                    FOREIGN KEY (approved_by) REFERENCES users(id)
                )
            """)
        print("   ✅ product_sales table created")
        
        # 2. Create sale_suggestions table (auto-generated suggestions)
        print("2. Creating sale_suggestions table...")
        if DB_ENGINE == 'mysql':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sale_suggestions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    suggested_discount DECIMAL(5,2) NOT NULL,
                    suggested_price DECIMAL(10,2) NOT NULL,
                    days_until_expiry INT NOT NULL,
                    reason TEXT,
                    seller_id INT NOT NULL,
                    notification_sent BOOLEAN DEFAULT 0,
                    seller_viewed BOOLEAN DEFAULT 0,
                    seller_action VARCHAR(20) DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NULL,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                    FOREIGN KEY (seller_id) REFERENCES users(id),
                    INDEX idx_seller_pending (seller_id, seller_action),
                    INDEX idx_expiry (days_until_expiry)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sale_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    suggested_discount REAL NOT NULL,
                    suggested_price REAL NOT NULL,
                    days_until_expiry INTEGER NOT NULL,
                    reason TEXT,
                    seller_id INTEGER NOT NULL,
                    notification_sent INTEGER DEFAULT 0,
                    seller_viewed INTEGER DEFAULT 0,
                    seller_action TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NULL,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                    FOREIGN KEY (seller_id) REFERENCES users(id)
                )
            """)
        print("   ✅ sale_suggestions table created")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Migration completed successfully!\n")
        print("Tables created:")
        print("  - product_sales: Store approved/pending sale requests")
        print("  - sale_suggestions: Auto-generated discount suggestions\n")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}\n")
        raise

if __name__ == '__main__':
    run_migration()
