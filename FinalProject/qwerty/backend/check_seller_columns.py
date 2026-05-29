#!/usr/bin/env python3
"""Check what columns exist in the sellers table"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import pymysql
import pymysql.cursors

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

def check_columns():
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
        
        # Get column information
        cursor.execute("SHOW COLUMNS FROM sellers")
        columns = cursor.fetchall()
        
        print("📋 Columns in 'sellers' table:")
        for col in columns:
            print(f"   - {col['Field']} ({col['Type']}) - Default: {col.get('Default', 'NULL')}")
        
        # Check seller data
        cursor.execute('SELECT * FROM sellers WHERE id = 3')
        seller = cursor.fetchone()
        
        if seller:
            print(f"\n📊 Seller ID 3 data:")
            for key, value in seller.items():
                print(f"   {key}: {value}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_columns()

