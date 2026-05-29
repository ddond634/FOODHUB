"""Migration: Add missing profile/account columns across users, sellers, riders.
Idempotent: checks existence before adding.
"""
import os
import sqlite3

try:
    import pymysql
except ImportError:
    pymysql = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ENGINE = os.environ.get('DB_ENGINE','sqlite').lower()

USER_COLUMNS = [
    ('phone','TEXT'),
    ('avatar_url','TEXT'),
    ('gender','TEXT'),
    ('birthdate','TEXT'),
    ('address_line1','TEXT'),
    ('address_line2','TEXT'),
    ('city','TEXT'),
    ('province','TEXT'),
    ('region','TEXT'),
    ('postal_code','TEXT')
]

SELLER_COLUMNS = [
    ('store_name','TEXT'),
    ('store_description','TEXT'),
    ('store_logo','TEXT'),
    ('store_banner','TEXT'),
    ('support_phone','TEXT'),
    ('support_email','TEXT'),
    ('tax_id','TEXT'),
    ('payout_method','TEXT'),
    ('bank_account_name','TEXT'),
    ('bank_account_number','TEXT')
]

RIDER_COLUMNS = [
    ('phone','TEXT'),
    ('avatar_url','TEXT'),
    ('address_line1','TEXT'),
    ('city','TEXT'),
    ('province','TEXT'),
    ('region','TEXT'),
    ('status','TEXT'),
    ('license_expiry','TEXT')
]

def column_exists_sqlite(cur, table, col):
    cur.execute(f"PRAGMA table_info('{table}')")
    return any(r[1] == col for r in cur.fetchall())

def column_exists_mysql(cur, table, col):
    cur.execute(f"SHOW COLUMNS FROM {table} LIKE '{col}'")
    return cur.fetchone() is not None

def migrate_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # users
    for col, ctype in USER_COLUMNS:
        if not column_exists_sqlite(cur,'users',col):
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
            print(f"[sqlite] users.{col} added")
    # sellers
    for col, ctype in SELLER_COLUMNS:
        if not column_exists_sqlite(cur,'sellers',col):
            cur.execute(f"ALTER TABLE sellers ADD COLUMN {col} {ctype}")
            print(f"[sqlite] sellers.{col} added")
    # riders
    for col, ctype in RIDER_COLUMNS:
        if not column_exists_sqlite(cur,'riders',col):
            cur.execute(f"ALTER TABLE riders ADD COLUMN {col} {ctype}")
            print(f"[sqlite] riders.{col} added")
    conn.commit(); conn.close()
    print('Profile columns migration complete (sqlite)')

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
    # users
    for col, ctype in USER_COLUMNS:
        if not column_exists_mysql(cur,'users',col):
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} VARCHAR(255) NULL")
            print(f"[mysql] users.{col} added")
    # sellers
    for col, ctype in SELLER_COLUMNS:
        if not column_exists_mysql(cur,'sellers',col):
            # Lengths tuned to usage (descriptions larger)
            if col in ('store_description',):
                cur.execute(f"ALTER TABLE sellers ADD COLUMN {col} TEXT NULL")
            else:
                cur.execute(f"ALTER TABLE sellers ADD COLUMN {col} VARCHAR(255) NULL")
            print(f"[mysql] sellers.{col} added")
    # riders
    for col, ctype in RIDER_COLUMNS:
        if not column_exists_mysql(cur,'riders',col):
            cur.execute(f"ALTER TABLE riders ADD COLUMN {col} VARCHAR(255) NULL")
            print(f"[mysql] riders.{col} added")
    conn.commit(); conn.close()
    print('Profile columns migration complete (mysql)')

if __name__ == '__main__':
    if DB_ENGINE == 'mysql':
        migrate_mysql()
    else:
        migrate_sqlite(os.path.join(BASE_DIR,'qwerty.db'))
