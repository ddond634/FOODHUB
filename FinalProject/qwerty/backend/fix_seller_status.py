#!/usr/bin/env python3
"""
Script to manually fix seller status to 'banned'
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import pymysql
import pymysql.cursors

# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

def fix_seller_status():
    """Fix seller status for Test Store One"""
    try:
        conn = pymysql.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASS', ''),
            db=os.environ.get('DB_NAME', 'qwerty'),
            port=int(os.environ.get('DB_PORT', '3306')),
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # Find the seller
        cursor.execute('SELECT id, business_name, shop_status FROM sellers WHERE business_name LIKE %s', ('%Test Store One%',))
        seller = cursor.fetchone()
        
        if not seller:
            print("❌ Seller 'Test Store One' not found")
            return False
        
        print(f"📋 Found seller: ID={seller['id']}, Name={seller['business_name']}, Current Status={seller['shop_status']}")
        
        # Update to banned
        cursor.execute('UPDATE sellers SET shop_status = %s WHERE id = %s', ('banned', seller['id']))
        conn.commit()
        
        # Verify
        cursor.execute('SELECT shop_status FROM sellers WHERE id = %s', (seller['id'],))
        updated = cursor.fetchone()
        
        print(f"✅ Updated seller {seller['id']} status to: {updated['shop_status']}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Fixing seller status for Test Store One...\n")
    success = fix_seller_status()
    sys.exit(0 if success else 1)

