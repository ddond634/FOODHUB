"""Migration: Add shipping columns (free_shipping_threshold, standard_shipping_fee) to sellers table.
Idempotent for SQLite & MySQL.
"""
import os, sqlite3
try:
    import pymysql
except ImportError:
    pymysql = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ENGINE = os.environ.get('DB_ENGINE','sqlite').lower()

SQLITE_COLUMNS = [
    ('free_shipping_threshold','REAL'),
    ('standard_shipping_fee','REAL')
]
MYSQL_COLUMNS = [
    ('free_shipping_threshold','DECIMAL(12,2)'),
    ('standard_shipping_fee','DECIMAL(12,2)')
]

def sqlite_column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info('{table}')")
    return any(r[1] == col for r in cur.fetchall())

def migrate_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for col, ctype in SQLITE_COLUMNS:
        if not sqlite_column_exists(cur,'sellers',col):
            cur.execute(f"ALTER TABLE sellers ADD COLUMN {col} {ctype}")
            print(f"[sqlite] sellers.{col} added")
    conn.commit(); conn.close()
    print('Shipping columns migration complete (sqlite)')

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
    for col, ctype in MYSQL_COLUMNS:
        cur.execute(f"SHOW COLUMNS FROM sellers LIKE '{col}'")
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE sellers ADD COLUMN {col} {ctype} NULL")
            print(f"[mysql] sellers.{col} added")
    conn.commit(); conn.close()
    print('Shipping columns migration complete (mysql)')

if __name__ == '__main__':
    if DB_ENGINE == 'mysql':
        migrate_mysql()
    else:
        migrate_sqlite(os.path.join(BASE_DIR,'qwerty.db'))
