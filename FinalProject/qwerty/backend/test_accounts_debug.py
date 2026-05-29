#!/usr/bin/env python3
"""
Debug script to check if test accounts exist and create them if needed
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import database connection
from server import get_db, DB_ENGINE

def check_and_create_accounts():
    db = get_db()
    cursor = db.cursor()
    
    print("🔍 Checking for test accounts...\n")
    
    # Check sellers
    if DB_ENGINE == 'mysql':
        cursor.execute("""
            SELECT s.id, s.user_id, s.business_name, s.shop_status, u.email
            FROM sellers s
            INNER JOIN users u ON s.user_id = u.id
            WHERE u.email LIKE 'test-seller-%@test.com'
        """)
    else:
        cursor.execute("""
            SELECT s.id, s.user_id, s.business_name, s.shop_status, u.email
            FROM sellers s
            INNER JOIN users u ON s.user_id = u.id
            WHERE u.email LIKE 'test-seller-%@test.com'
        """)
    
    sellers = cursor.fetchall()
    print(f"📊 Found {len(sellers)} test seller accounts:")
    for seller in sellers:
        print(f"   - {seller}")
    
    # Check riders
    if DB_ENGINE == 'mysql':
        cursor.execute("""
            SELECT r.id, r.user_id, r.vehicle_type, r.rider_status, u.email
            FROM riders r
            INNER JOIN users u ON r.user_id = u.id
            WHERE u.email LIKE 'test-rider-%@test.com'
        """)
    else:
        cursor.execute("""
            SELECT r.id, r.user_id, r.vehicle_type, r.rider_status, u.email
            FROM riders r
            INNER JOIN users u ON r.user_id = u.id
            WHERE u.email LIKE 'test-rider-%@test.com'
        """)
    
    riders = cursor.fetchall()
    print(f"\n📊 Found {len(riders)} test rider accounts:")
    for rider in riders:
        print(f"   - {rider}")
    
    cursor.close()
    db.close()
    
    if len(sellers) < 3 or len(riders) < 3:
        print("\n⚠️  Not all test accounts found. Please run the create endpoint again.")
    else:
        print("\n✅ All test accounts exist!")

if __name__ == "__main__":
    check_and_create_accounts()

