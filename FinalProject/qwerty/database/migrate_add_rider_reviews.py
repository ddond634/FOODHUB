"""Migration: Create rider_reviews table for customer ratings.
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

def create_rider_reviews_table():
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
        
        if not table_exists_mysql(cur, 'rider_reviews'):
            cur.execute("""
                CREATE TABLE rider_reviews (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    rider_id INT NOT NULL,
                    customer_id INT NOT NULL,
                    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (rider_id) REFERENCES riders(id) ON DELETE CASCADE,
                    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_order_review (order_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("[mysql] Created rider_reviews table")
        else:
            print("[mysql] rider_reviews table already exists")
        
        conn.commit()
        conn.close()
        print('Rider reviews table migration complete!')
    else:  # SQLite
        db_path = os.path.join(BASE_DIR, 'qwerty.db')
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        if not table_exists_sqlite(cur, 'rider_reviews'):
            cur.execute("""
                CREATE TABLE rider_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    rider_id INTEGER NOT NULL,
                    customer_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (rider_id) REFERENCES riders(id) ON DELETE CASCADE,
                    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(order_id)
                )
            """)
            print("[sqlite] Created rider_reviews table")
        else:
            print("[sqlite] rider_reviews table already exists")
        
        conn.commit()
        conn.close()
        print('Rider reviews table migration complete!')

if __name__ == '__main__':
    create_rider_reviews_table()

