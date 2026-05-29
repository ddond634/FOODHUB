"""Migration: Add store_id column to products to link products to specific stores.
Supports SQLite and MySQL.
"""
import os
import sqlite3

try:
    import pymysql
except ImportError:
    pymysql = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ENGINE = os.environ.get('DB_ENGINE','sqlite').lower()

def migrate_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info('products')")
    cols = [row[1] for row in cur.fetchall()]
    if 'store_id' in cols:
        print('[products.store_id] already exists (sqlite), skipping')
        conn.close()
        return
    cur.execute("ALTER TABLE products ADD COLUMN store_id INTEGER REFERENCES stores(id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_products_store ON products(store_id)")
    conn.commit()
    conn.close()
    print('[products.store_id] added (sqlite)')

def migrate_mysql():
    if not pymysql:
        raise RuntimeError('pymysql not installed')
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
    cur.execute("SHOW COLUMNS FROM products LIKE 'store_id'")
    if cur.fetchone():
        print('[products.store_id] already exists (mysql), skipping')
        conn.close()
        return
    cur.execute("ALTER TABLE products ADD COLUMN store_id INT NULL")
    cur.execute("ALTER TABLE products ADD CONSTRAINT fk_products_store FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL")
    cur.execute("CREATE INDEX idx_products_store ON products(store_id)")
    conn.commit()
    conn.close()
    print('[products.store_id] added (mysql)')

if __name__ == '__main__':
    if DB_ENGINE == 'mysql':
        migrate_mysql()
    else:
        migrate_sqlite(os.path.join(BASE_DIR,'qwerty.db'))
