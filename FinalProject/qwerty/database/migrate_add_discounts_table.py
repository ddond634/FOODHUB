"""Migration: Add discounts table for seller-created promotions requiring admin approval.
Supports SQLite and MySQL.
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

# Schema
# discounts(
#   id PK,
#   seller_user_id int not null,
#   name varchar,
#   description text,
#   discount_type enum('percent','fixed'),
#   value decimal(10,2),
#   status enum('pending','approved','declined') default 'pending',
#   admin_note text null,
#   start_at datetime,
#   end_at datetime,
#   created_at datetime,
# )
# discount_products(
#   id PK,
#   discount_id FK -> discounts(id),
#   product_id FK -> products(id)
# )


def migrate_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # discounts
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='discounts'")
    if not cur.fetchone():
        cur.execute(
            '''CREATE TABLE discounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                discount_type TEXT CHECK(discount_type IN ('percent','fixed')) NOT NULL,
                value REAL NOT NULL,
                status TEXT CHECK(status IN ('pending','approved','declined')) DEFAULT 'pending',
                admin_note TEXT,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(seller_user_id) REFERENCES users(id) ON DELETE CASCADE
            )'''
        )
        cur.execute("CREATE INDEX idx_discounts_seller ON discounts(seller_user_id)")
        cur.execute("CREATE INDEX idx_discounts_status ON discounts(status)")
    # discount_products
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='discount_products'")
    if not cur.fetchone():
        cur.execute(
            '''CREATE TABLE discount_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discount_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                FOREIGN KEY(discount_id) REFERENCES discounts(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            )'''
        )
        cur.execute("CREATE INDEX idx_discount_products_did ON discount_products(discount_id)")
        cur.execute("CREATE INDEX idx_discount_products_pid ON discount_products(product_id)")
    conn.commit()
    conn.close()
    print('[discounts] tables ensured (sqlite)')


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
    # discounts
    cur.execute("SHOW TABLES LIKE 'discounts'")
    if not cur.fetchone():
        cur.execute(
            '''CREATE TABLE discounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                seller_user_id INT NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                discount_type ENUM('percent','fixed') NOT NULL,
                value DECIMAL(10,2) NOT NULL,
                status ENUM('pending','approved','declined') DEFAULT 'pending',
                admin_note TEXT,
                start_at DATETIME NOT NULL,
                end_at DATETIME NOT NULL,
                created_at DATETIME NOT NULL,
                CONSTRAINT fk_discounts_user FOREIGN KEY (seller_user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''
        )
        cur.execute("CREATE INDEX idx_discounts_seller ON discounts(seller_user_id)")
        cur.execute("CREATE INDEX idx_discounts_status ON discounts(status)")
    # discount_products
    cur.execute("SHOW TABLES LIKE 'discount_products'")
    if not cur.fetchone():
        cur.execute(
            '''CREATE TABLE discount_products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                discount_id INT NOT NULL,
                product_id INT NOT NULL,
                CONSTRAINT fk_dp_discount FOREIGN KEY (discount_id) REFERENCES discounts(id) ON DELETE CASCADE,
                CONSTRAINT fk_dp_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'''
        )
        cur.execute("CREATE INDEX idx_discount_products_did ON discount_products(discount_id)")
        cur.execute("CREATE INDEX idx_discount_products_pid ON discount_products(product_id)")
    conn.commit()
    conn.close()
    print('[discounts] tables ensured (mysql)')


if __name__ == '__main__':
    if DB_ENGINE == 'mysql':
        migrate_mysql()
    else:
        migrate_sqlite(os.path.join(BASE_DIR,'qwerty.db'))
