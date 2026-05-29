#!/usr/bin/env python3
"""
Migration: Add quantity and price_total columns to wishlist table
- Adds columns if missing
- Initializes existing rows: quantity=1, price_total=products.price * 1 when possible
"""
import pymysql
import sqlite3
import os

DB_ENGINE = os.environ.get('DB_ENGINE','mysql')

MYSQL_CONFIG = dict(host='localhost', user='root', password='', database='qwerty', port=3306)


def mysql_migrate():
    conn = pymysql.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    print('🔧 Migrating wishlist table (MySQL)...')

    # Check columns
    cur.execute("SHOW COLUMNS FROM wishlist")
    cols = {row[0] for row in cur.fetchall()}

    # Add quantity
    if 'quantity' not in cols:
        cur.execute("ALTER TABLE wishlist ADD COLUMN quantity INT NOT NULL DEFAULT 1 AFTER product_id")
        print('  ✅ Added column: quantity')

    # Add price_total
    if 'price_total' not in cols:
        cur.execute("ALTER TABLE wishlist ADD COLUMN price_total DECIMAL(10,2) NOT NULL DEFAULT 0.00 AFTER quantity")
        print('  ✅ Added column: price_total')

    # Initialize price_total from products.price when possible
    cur.execute(
        """
        UPDATE wishlist w
        JOIN products p ON p.id = w.product_id
        SET w.price_total = ROUND(p.price * w.quantity, 2)
        """
    )
    print('  🔄 Initialized price_total from product price')

    conn.commit()
    cur.close()
    conn.close()
    print('✅ Migration complete (MySQL)')


def sqlite_migrate():
    # Detect DB file
    db_path = os.path.join(os.getcwd(), 'database', 'qwerty.sqlite3')
    if not os.path.exists(db_path):
        db_path = os.path.join(os.getcwd(), 'qwerty.sqlite3')
    print(f'🔧 Migrating wishlist table (SQLite): {db_path}')

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get columns
    cur.execute("PRAGMA table_info(wishlist)")
    cols = {row[1] for row in cur.fetchall()}

    if 'quantity' not in cols:
        cur.execute("ALTER TABLE wishlist ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")
        print('  ✅ Added column: quantity')

    if 'price_total' not in cols:
        cur.execute("ALTER TABLE wishlist ADD COLUMN price_total REAL NOT NULL DEFAULT 0.0")
        print('  ✅ Added column: price_total')

    cur.execute(
        """
        UPDATE wishlist
        SET price_total = ROUND((SELECT price FROM products WHERE products.id = wishlist.product_id) * quantity, 2)
        """
    )
    print('  🔄 Initialized price_total from product price')

    conn.commit()
    cur.close()
    conn.close()
    print('✅ Migration complete (SQLite)')


if __name__ == '__main__':
    if DB_ENGINE == 'mysql':
        mysql_migrate()
    else:
        sqlite_migrate()
