#!/usr/bin/env python3
"""
Script to alter the shop_status ENUM to include 'banned' and 'warning'
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import pymysql
import pymysql.cursors

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

def fix_enum():
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
        
        print("🔧 Altering shop_status ENUM to include 'banned' and 'warning'...")
        
        # Alter the ENUM to include banned and warning
        cursor.execute("""
            ALTER TABLE sellers 
            MODIFY COLUMN shop_status 
            ENUM('pending','active','suspended','declined','resubmitted','warning','banned') 
            DEFAULT 'pending'
        """)
        
        conn.commit()
        print("✅ Successfully updated shop_status ENUM")
        
        # Now update Test Store One to banned
        cursor.execute("UPDATE sellers SET shop_status = 'banned' WHERE id = 3")
        conn.commit()
        
        # Verify
        cursor.execute('SELECT id, business_name, shop_status FROM sellers WHERE id = 3')
        seller = cursor.fetchone()
        print(f"✅ Seller {seller['id']} ({seller['business_name']}) status is now: {seller['shop_status']}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_enum()
    sys.exit(0 if success else 1)

