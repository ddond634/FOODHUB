#!/usr/bin/env python3
"""
Database Utilities - Consolidated check, verify, and fix functions
Consolidates: check_tables, check_db_engine, check_qwerty_db, check_seller_status,
              check_wishlist, verify_tables, fix_columns, fix_seller_verification
"""

import sqlite3
import pymysql
import pymysql.cursors
import sys
import os

# Add backend to path for server imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Database configuration (MySQL)
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'qwerty',
    'cursorclass': pymysql.cursors.DictCursor
}


# ============================================================================
# SQLite Check Functions
# ============================================================================

def check_hub_db_tables():
    """Check tables in hub.db (SQLite)"""
    try:
        conn = sqlite3.connect('hub.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print("Tables in hub.db:")
        for table in tables:
            print(f"  - {table}")
        conn.close()
        return tables
    except Exception as e:
        print(f"Error checking hub.db: {e}")
        return []


def check_qwerty_db_tables():
    """Check tables in qwerty.db (SQLite)"""
    try:
        conn = sqlite3.connect('qwerty.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print('Tables in qwerty.db:')
        for table in tables:
            print(f'  - {table[0]}')
        print(f'\nTotal: {len(tables)} tables')
        conn.close()
        return [t[0] for t in tables]
    except Exception as e:
        print(f"Error checking qwerty.db: {e}")
        return []


def verify_sqlite_tables():
    """Verify tables in hub.db (SQLite)"""
    try:
        conn = sqlite3.connect('hub.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print('Tables in hub.db:')
        for table in tables:
            print(f'  - {table[0]}')
        print(f'\nTotal: {len(tables)} tables')
        conn.close()
        return [t[0] for t in tables]
    except Exception as e:
        print(f"Error verifying tables: {e}")
        return []


# ============================================================================
# Database Engine Check
# ============================================================================

def check_db_configuration():
    """Check database engine configuration from server.py"""
    try:
        from backend.server import app, DB_ENGINE, DB_PATH
        
        print(f"DB_ENGINE: {DB_ENGINE}")
        print(f"DB_PATH: {DB_PATH}")
        print(f"DB file exists: {os.path.exists(DB_PATH)}")
        
        return {
            'engine': DB_ENGINE,
            'path': DB_PATH,
            'exists': os.path.exists(DB_PATH)
        }
    except Exception as e:
        print(f"Error checking DB configuration: {e}")
        return None


# ============================================================================
# MySQL Check Functions
# ============================================================================

def check_seller_status():
    """Check and display seller status from MySQL"""
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Get all sellers with their user info
        cursor.execute('''
            SELECT 
                s.id as seller_id,
                s.user_id,
                s.business_name,
                s.verified,
                s.shop_status,
                u.email,
                u.role
            FROM sellers s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.id
        ''')
        
        sellers = cursor.fetchall()
        
        print("\n=== SELLER STATUS REPORT ===\n")
        for seller in sellers:
            print(f"Seller ID: {seller['seller_id']}")
            print(f"Business: {seller['business_name']}")
            print(f"Email: {seller['email']}")
            print(f"Verified: {seller['verified']}")
            print(f"Shop Status: {seller['shop_status']}")
            print(f"User Role: {seller['role']}")
            print("-" * 50)
        
        cursor.close()
        conn.close()
        return sellers
        
    except Exception as e:
        print(f"Error checking seller status: {e}")
        return None


def check_wishlist():
    """Check wishlist and sample products from MySQL"""
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Check wishlist table
        cursor.execute('SELECT * FROM wishlist')
        wishlist_items = cursor.fetchall()
        
        print("\n=== WISHLIST TABLE ===")
        print(f"Total items: {len(wishlist_items)}")
        
        if wishlist_items:
            for item in wishlist_items:
                print(f"\nWishlist Entry:")
                print(f"  ID: {item['id']}")
                print(f"  User ID: {item['user_id']}")
                print(f"  Product ID: {item['product_id']}")
                print(f"  Created: {item['created_at']}")
        else:
            print("  (empty)")
        
        # Check products table
        cursor.execute('SELECT id, title, price FROM products LIMIT 5')
        products = cursor.fetchall()
        
        print("\n=== SAMPLE PRODUCTS ===")
        for prod in products:
            print(f"  ID {prod['id']}: {prod['title']} - ₱{prod['price']}")
        
        cursor.close()
        conn.close()
        return {'wishlist': wishlist_items, 'products': products}
        
    except Exception as e:
        print(f"Error checking wishlist: {e}")
        return None


# ============================================================================
# Fix Functions
# ============================================================================

def fix_messaging_api_columns():
    """Fix column names in messaging_api.py to match database schema"""
    try:
        filepath = 'backend/messaging_api.py'
        
        # Read the file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Track changes
        original_content = content
        
        # Replace all occurrences
        content = content.replace('sender_role', 'sender_type')
        content = content.replace('message_text', 'message')
        content = content.replace('read_status', 'is_read')
        
        # Write back if there were changes
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Fixed all column names in messaging_api.py")
            print("   - sender_role → sender_type")
            print("   - message_text → message")
            print("   - read_status → is_read")
            return True
        else:
            print("ℹ️  No changes needed in messaging_api.py")
            return True
            
    except Exception as e:
        print(f"Error fixing messaging_api columns: {e}")
        return False


def fix_seller_verification(seller_id=1):
    """Update seller verification status in MySQL"""
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Update seller to be verified
        cursor.execute('''
            UPDATE sellers 
            SET verified = 1
            WHERE id = %s
        ''', (seller_id,))
        
        conn.commit()
        
        # Verify the update
        cursor.execute('SELECT id, business_name, verified, shop_status FROM sellers WHERE id = %s', (seller_id,))
        seller = cursor.fetchone()
        
        if seller:
            print(f"\n✅ Updated Seller Status:")
            print(f"   ID: {seller['id']}")
            print(f"   Business: {seller['business_name']}")
            print(f"   Verified: {seller['verified']} ✓")
            print(f"   Shop Status: {seller['shop_status']}")
            print(f"\n🎉 Seller can now create products!")
        
        cursor.close()
        conn.close()
        return seller
        
    except Exception as e:
        print(f"❌ Error updating seller verification: {e}")
        return None


# ============================================================================
# CLI Entry Points
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Utilities')
    parser.add_argument('command', 
                        choices=['check-hub', 'check-qwerty', 'check-config', 
                                'check-sellers', 'check-wishlist', 'verify-tables',
                                'fix-messaging', 'fix-seller'],
                        help='Command to execute')
    parser.add_argument('--seller-id', type=int, default=1, help='Seller ID for fix-seller command')
    
    args = parser.parse_args()
    
    if args.command == 'check-hub':
        check_hub_db_tables()
    elif args.command == 'check-qwerty':
        check_qwerty_db_tables()
    elif args.command == 'check-config':
        check_db_configuration()
    elif args.command == 'check-sellers':
        check_seller_status()
    elif args.command == 'check-wishlist':
        check_wishlist()
    elif args.command == 'verify-tables':
        verify_sqlite_tables()
    elif args.command == 'fix-messaging':
        fix_messaging_api_columns()
    elif args.command == 'fix-seller':
        fix_seller_verification(args.seller_id)
