"""Migration: Update return_refund_requests table to add seller response and tracking fields.
Idempotent: checks existence before adding columns.
"""
import os
import sqlite3

try:
    import pymysql
except ImportError:
    pymysql = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

def column_exists_sqlite(cur, table, column):
    cur.execute("PRAGMA table_info(?)", (table,))
    columns = [row[1] for row in cur.fetchall()]
    return column in columns

def column_exists_mysql(cur, table, column):
    cur.execute("SHOW COLUMNS FROM %s LIKE %s" % (table, "'" + column + "'"))
    return cur.fetchone() is not None

def update_return_refund_requests_table():
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
        
        # Add seller_response column
        if not column_exists_mysql(cur, 'return_refund_requests', 'seller_response'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN seller_response ENUM('pending', 'approved', 'rejected', 'request_info') DEFAULT 'pending' AFTER status")
            print("[mysql] Added seller_response column")
        
        # Add rejection_reason column
        if not column_exists_mysql(cur, 'return_refund_requests', 'rejection_reason'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN rejection_reason TEXT AFTER seller_response")
            print("[mysql] Added rejection_reason column")
        
        # Add pickup_rider_id column
        if not column_exists_mysql(cur, 'return_refund_requests', 'pickup_rider_id'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN pickup_rider_id INT NULL AFTER seller_response")
            cur.execute("ALTER TABLE return_refund_requests ADD FOREIGN KEY (pickup_rider_id) REFERENCES riders(id) ON DELETE SET NULL")
            print("[mysql] Added pickup_rider_id column")
        
        # Add pickup_scheduled_at column
        if not column_exists_mysql(cur, 'return_refund_requests', 'pickup_scheduled_at'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN pickup_scheduled_at DATETIME NULL AFTER pickup_rider_id")
            print("[mysql] Added pickup_scheduled_at column")
        
        # Add pickup_completed_at column
        if not column_exists_mysql(cur, 'return_refund_requests', 'pickup_completed_at'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN pickup_completed_at DATETIME NULL AFTER pickup_scheduled_at")
            print("[mysql] Added pickup_completed_at column")
        
        # Add item_received_at column
        if not column_exists_mysql(cur, 'return_refund_requests', 'item_received_at'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN item_received_at DATETIME NULL AFTER pickup_completed_at")
            print("[mysql] Added item_received_at column")
        
        # Add refund_processed_at column
        if not column_exists_mysql(cur, 'return_refund_requests', 'refund_processed_at'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN refund_processed_at DATETIME NULL AFTER item_received_at")
            print("[mysql] Added refund_processed_at column")
        
        # Add evidence_images column
        if not column_exists_mysql(cur, 'return_refund_requests', 'evidence_images'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN evidence_images TEXT COMMENT 'JSON array of image paths' AFTER reason")
            print("[mysql] Added evidence_images column")
        
        conn.commit()
        conn.close()
        print('Return/Refund requests table update complete!')
    else:  # SQLite
        db_path = os.path.join(BASE_DIR, 'qwerty.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Add seller_response column
        if not column_exists_sqlite(cur, 'return_refund_requests', 'seller_response'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN seller_response TEXT DEFAULT 'pending' CHECK(seller_response IN ('pending', 'approved', 'rejected', 'request_info'))")
            print("[sqlite] Added seller_response column")
        
        # Add rejection_reason column
        if not column_exists_sqlite(cur, 'return_refund_requests', 'rejection_reason'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN rejection_reason TEXT")
            print("[sqlite] Added rejection_reason column")
        
        # Add pickup_rider_id column
        if not column_exists_sqlite(cur, 'return_refund_requests', 'pickup_rider_id'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN pickup_rider_id INTEGER NULL")
            print("[sqlite] Added pickup_rider_id column")
        
        # Add pickup_scheduled_at column
        if not column_exists_sqlite(cur, 'return_refund_requests', 'pickup_scheduled_at'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN pickup_scheduled_at TEXT NULL")
            print("[sqlite] Added pickup_scheduled_at column")
        
        # Add pickup_completed_at column
        if not column_exists_sqlite(cur, 'return_refund_requests', 'pickup_completed_at'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN pickup_completed_at TEXT NULL")
            print("[sqlite] Added pickup_completed_at column")
        
        # Add item_received_at column
        if not column_exists_sqlite(cur, 'return_refund_requests', 'item_received_at'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN item_received_at TEXT NULL")
            print("[sqlite] Added item_received_at column")
        
        # Add refund_processed_at column
        if not column_exists_sqlite(cur, 'return_refund_requests', 'refund_processed_at'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN refund_processed_at TEXT NULL")
            print("[sqlite] Added refund_processed_at column")
        
        # Add evidence_images column
        if not column_exists_sqlite(cur, 'return_refund_requests', 'evidence_images'):
            cur.execute("ALTER TABLE return_refund_requests ADD COLUMN evidence_images TEXT")
            print("[sqlite] Added evidence_images column")
        
        conn.commit()
        conn.close()
        print('Return/Refund requests table update complete!')

if __name__ == '__main__':
    update_return_refund_requests_table()

