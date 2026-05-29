#!/usr/bin/env python3
"""
Test script to verify if inputs are being saved to the database.
This script checks:
1. Database connection
2. Recent orders
3. Recent order items
4. Recent user registrations
5. Product inventory updates
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BASE_DIR)

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

if DB_ENGINE == 'mysql':
    import pymysql
    MYSQL_CONFIG = {
        'host': os.environ.get('DB_HOST', '127.0.0.1'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASS', ''),
        'db': os.environ.get('DB_NAME', 'qwerty'),
        'port': int(os.environ.get('DB_PORT', '3306')),
        'cursorclass': pymysql.cursors.DictCursor,
    }
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        print("✓ MySQL connection successful")
    except Exception as e:
        print(f"✗ MySQL connection failed: {e}")
        sys.exit(1)
else:
    import sqlite3
    DB_PATH = os.path.join(BASE_DIR, 'qwerty.db')
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        print("✓ SQLite connection successful")
    except Exception as e:
        print(f"✗ SQLite connection failed: {e}")
        sys.exit(1)

cur = conn.cursor()

print("\n" + "="*60)
print("DATABASE INPUT VERIFICATION REPORT")
print("="*60)

# 1. Check recent orders (last 24 hours)
print("\n1. RECENT ORDERS (last 24 hours):")
print("-" * 60)
try:
    if DB_ENGINE == 'mysql':
        cur.execute("""
            SELECT id, customer_name, customer_phone, total, status, created_at 
            FROM orders 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY created_at DESC 
            LIMIT 10
        """)
    else:
        cur.execute("""
            SELECT id, customer_name, customer_phone, total, status, created_at 
            FROM orders 
            WHERE datetime(created_at) >= datetime('now', '-24 hours')
            ORDER BY created_at DESC 
            LIMIT 10
        """)
    orders = cur.fetchall()
    if orders:
        for order in orders:
            if DB_ENGINE == 'mysql':
                print(f"  Order #{order['id']}: {order['customer_name']} - ₱{order['total']:.2f} - {order['status']} - {order['created_at']}")
            else:
                print(f"  Order #{order['id']}: {order['customer_name']} - ₱{order['total']:.2f} - {order['status']} - {order['created_at']}")
    else:
        print("  ⚠ No orders found in the last 24 hours")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 2. Check order items
print("\n2. RECENT ORDER ITEMS:")
print("-" * 60)
try:
    if DB_ENGINE == 'mysql':
        cur.execute("""
            SELECT oi.id, oi.order_id, oi.product_id, oi.quantity, oi.price, o.customer_name
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY o.created_at DESC
            LIMIT 10
        """)
    else:
        cur.execute("""
            SELECT oi.id, oi.order_id, oi.product_id, oi.quantity, oi.price, o.customer_name
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE datetime(o.created_at) >= datetime('now', '-24 hours')
            ORDER BY o.created_at DESC
            LIMIT 10
        """)
    items = cur.fetchall()
    if items:
        for item in items:
            if DB_ENGINE == 'mysql':
                pid = item['product_id'] if item['product_id'] else 'NULL'
                print(f"  Item #{item['id']}: Order {item['order_id']} - Product {pid} - Qty: {item['quantity']} - ₱{item['price']:.2f}")
            else:
                pid = item['product_id'] if item['product_id'] else 'NULL'
                print(f"  Item #{item['id']}: Order {item['order_id']} - Product {pid} - Qty: {item['quantity']} - ₱{item['price']:.2f}")
    else:
        print("  ⚠ No order items found in the last 24 hours")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 3. Check for NULL product_id in order_items (potential issue)
print("\n3. ORDER ITEMS WITH NULL PRODUCT_ID (potential issue):")
print("-" * 60)
try:
    if DB_ENGINE == 'mysql':
        cur.execute("SELECT COUNT(*) as count FROM order_items WHERE product_id IS NULL")
    else:
        cur.execute("SELECT COUNT(*) as count FROM order_items WHERE product_id IS NULL")
    result = cur.fetchone()
    count = result['count'] if DB_ENGINE == 'mysql' else result[0]
    if count > 0:
        print(f"  ⚠ WARNING: {count} order items have NULL product_id")
        print("     This means inventory won't be updated for these items")
    else:
        print("  ✓ All order items have product_id")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 4. Check recent user registrations
print("\n4. RECENT USER REGISTRATIONS (last 24 hours):")
print("-" * 60)
try:
    if DB_ENGINE == 'mysql':
        cur.execute("""
            SELECT id, email, first_name, last_name, role, is_verified, created_at 
            FROM users 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY created_at DESC 
            LIMIT 10
        """)
    else:
        cur.execute("""
            SELECT id, email, first_name, last_name, role, is_verified, created_at 
            FROM users 
            WHERE datetime(created_at) >= datetime('now', '-24 hours')
            ORDER BY created_at DESC 
            LIMIT 10
        """)
    users = cur.fetchall()
    if users:
        for user in users:
            if DB_ENGINE == 'mysql':
                verified = "✓" if user['is_verified'] else "✗"
                print(f"  User #{user['id']}: {user['email']} ({user['role']}) - Verified: {verified} - {user['created_at']}")
            else:
                verified = "✓" if user['is_verified'] else "✗"
                print(f"  User #{user['id']}: {user['email']} ({user['role']}) - Verified: {verified} - {user['created_at']}")
    else:
        print("  ⚠ No new users registered in the last 24 hours")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 5. Check inventory movements
print("\n5. RECENT INVENTORY MOVEMENTS (last 24 hours):")
print("-" * 60)
try:
    if DB_ENGINE == 'mysql':
        cur.execute("""
            SELECT id, product_id, qty, movement_type, ref, created_at 
            FROM inventory_movements 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY created_at DESC 
            LIMIT 10
        """)
    else:
        cur.execute("""
            SELECT id, product_id, qty, movement_type, ref, created_at 
            FROM inventory_movements 
            WHERE datetime(created_at) >= datetime('now', '-24 hours')
            ORDER BY created_at DESC 
            LIMIT 10
        """)
    movements = cur.fetchall()
    if movements:
        for mov in movements:
            if DB_ENGINE == 'mysql':
                print(f"  Movement #{mov['id']}: Product {mov['product_id']} - {mov['qty']:+d} ({mov['movement_type']}) - {mov['ref']} - {mov['created_at']}")
            else:
                print(f"  Movement #{mov['id']}: Product {mov['product_id']} - {mov['qty']:+d} ({mov['movement_type']}) - {mov['ref']} - {mov['created_at']}")
    else:
        print("  ⚠ No inventory movements in the last 24 hours")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 6. Check total counts
print("\n6. DATABASE TOTALS:")
print("-" * 60)
try:
    tables = ['users', 'orders', 'order_items', 'products', 'inventory_movements']
    for table in tables:
        if DB_ENGINE == 'mysql':
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
        else:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
        result = cur.fetchone()
        count = result['count'] if DB_ENGINE == 'mysql' else result[0]
        print(f"  {table}: {count} records")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "="*60)
print("SUMMARY:")
print("="*60)
print("If you see:")
print("  ✓ Recent orders/items → Inputs ARE being saved")
print("  ⚠ No recent data → Either no activity or inputs NOT being saved")
print("  ⚠ NULL product_id → Frontend not sending product_id in cart items")
print("="*60)

cur.close()
conn.close()

