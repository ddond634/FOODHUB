"""Migration: Create return_refund_requests table for tracking return/refund requests.
Idempotent: checks existence before creating.
"""
import os
import sqlite3

try:
    import pymysql
except ImportError:
    pymysql = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

def table_exists_sqlite(cur, table):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None

def table_exists_mysql(cur, table):
    cur.execute("SHOW TABLES LIKE %s", (table,))
    return cur.fetchone() is not None

def create_return_refund_requests_table():
    if DB_ENGINE == 'mysql':
        conn = pymysql.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASS', ''),
            db=os.environ.get('DB_NAME', 'qwerty'),
            port=int(os.environ.get('DB_PORT', '3306')),
            cursorclass=pymysql.cursors.Cursor,
            charset='utf8mb4'
        )
        cur = conn.cursor()
        
        if not table_exists_mysql(cur, 'return_refund_requests'):
            cur.execute("""
                CREATE TABLE return_refund_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    order_item_id INT,
                    customer_id INT NOT NULL,
                    seller_id INT NOT NULL,
                    request_type ENUM('return', 'refund', 'both') NOT NULL DEFAULT 'return',
                    reason TEXT NOT NULL,
                    status ENUM('pending', 'approved', 'rejected', 'processing', 'completed', 'cancelled') NOT NULL DEFAULT 'pending',
                    admin_notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_order (order_id),
                    INDEX idx_customer (customer_id),
                    INDEX idx_seller (seller_id),
                    INDEX idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("[mysql] Created return_refund_requests table")
        else:
            print("[mysql] return_refund_requests table already exists")
        
        conn.commit()
        conn.close()
        print('Return/Refund requests table migration complete!')
    else:  # SQLite
        db_path = os.path.join(BASE_DIR, 'qwerty.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        if not table_exists_sqlite(cur, 'return_refund_requests'):
            cur.execute("""
                CREATE TABLE return_refund_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    order_item_id INTEGER,
                    customer_id INTEGER NOT NULL,
                    seller_id INTEGER NOT NULL,
                    request_type TEXT NOT NULL DEFAULT 'return' CHECK(request_type IN ('return', 'refund', 'both')),
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'processing', 'completed', 'cancelled')),
                    admin_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            # Create indexes
            cur.execute("CREATE INDEX idx_order ON return_refund_requests(order_id)")
            cur.execute("CREATE INDEX idx_customer ON return_refund_requests(customer_id)")
            cur.execute("CREATE INDEX idx_seller ON return_refund_requests(seller_id)")
            cur.execute("CREATE INDEX idx_status ON return_refund_requests(status)")
            print("[sqlite] Created return_refund_requests table")
        else:
            print("[sqlite] return_refund_requests table already exists")
        
        conn.commit()
        conn.close()
        print('Return/Refund requests table migration complete!')

if __name__ == '__main__':
    create_return_refund_requests_table()

