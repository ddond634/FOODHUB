"""Migration: Add stores table to support multiple stores per verified seller.
Handles both SQLite and MySQL.
"""
import os
import sqlite3
from datetime import datetime

try:
    import pymysql
except ImportError:
    pymysql = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

def migrate_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Check if table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stores'")
    if cur.fetchone():
        print('[stores] table already exists (sqlite), skipping')
        conn.close()
        return
    cur.execute(
        '''CREATE TABLE stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            logo TEXT,
            banner TEXT,
            category TEXT,
            region TEXT,
            province TEXT,
            city TEXT,
            status TEXT DEFAULT 'pending',
            approved_at TEXT,
            rejected_reason TEXT,
            created_at TEXT,
            FOREIGN KEY(seller_user_id) REFERENCES users(id) ON DELETE CASCADE
        )'''
    )
    cur.execute("CREATE INDEX idx_stores_seller ON stores(seller_user_id)")
    cur.execute("CREATE INDEX idx_stores_status ON stores(status)")
    conn.commit()
    conn.close()
    print('[stores] table created (sqlite)')

def migrate_mysql():
    if not pymysql:
        raise RuntimeError('pymysql not installed for MySQL migration')
    conn = pymysql.connect(
        host=os.environ.get('DB_HOST','127.0.0.1'),
        user=os.environ.get('DB_USER','root'),
        password=os.environ.get('DB_PASS',''),
        db=os.environ.get('DB_NAME','qwerty'),
        port=int(os.environ.get('DB_PORT','3306')),
        cursorclass=pymysql.cursors.Cursor,
        charset='utf8mb4'
    )
    cur = conn.cursor()
    cur.execute("SHOW TABLES LIKE 'stores'")
    if cur.fetchone():
        print('[stores] table already exists (mysql), skipping')
        conn.close()
        return
    cur.execute(
        '''CREATE TABLE stores (
            id INT AUTO_INCREMENT PRIMARY KEY,
            seller_user_id INT NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            logo VARCHAR(255),
            banner VARCHAR(255),
            category VARCHAR(100),
            region VARCHAR(100),
            province VARCHAR(100),
            city VARCHAR(100),
            status VARCHAR(20) DEFAULT 'pending',
            approved_at DATETIME NULL,
            rejected_reason VARCHAR(255),
            created_at DATETIME,
            CONSTRAINT fk_stores_user FOREIGN KEY (seller_user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''
    )
    cur.execute("CREATE INDEX idx_stores_seller ON stores(seller_user_id)")
    cur.execute("CREATE INDEX idx_stores_status ON stores(status)")
    conn.commit()
    conn.close()
    print('[stores] table created (mysql)')

if __name__ == '__main__':
    if DB_ENGINE == 'mysql':
        migrate_mysql()
    else:
        migrate_sqlite(os.path.join(BASE_DIR,'qwerty.db'))
