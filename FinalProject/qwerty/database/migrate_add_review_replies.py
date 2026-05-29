#!/usr/bin/env python3
"""
Add reply functionality to reviews tables
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_sqlite():
    """Add reply columns to SQLite reviews tables"""
    import sqlite3
    
    print("\n=== SQLite: Adding review reply columns ===\n")
    
    conn = sqlite3.connect('qwerty.db')
    cur = conn.cursor()
    
    try:
        # Add seller_reply and seller_reply_at to reviews table
        cur.execute("PRAGMA table_info(reviews)")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'seller_reply' not in columns:
            cur.execute("ALTER TABLE reviews ADD COLUMN seller_reply TEXT")
            print("✓ Added seller_reply column to reviews table")
        
        if 'seller_reply_at' not in columns:
            cur.execute("ALTER TABLE reviews ADD COLUMN seller_reply_at DATETIME")
            print("✓ Added seller_reply_at column to reviews table")
        
        # Add rider_reply and rider_reply_at to rider_reviews table
        cur.execute("PRAGMA table_info(rider_reviews)")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'rider_reply' not in columns:
            cur.execute("ALTER TABLE rider_reviews ADD COLUMN rider_reply TEXT")
            print("✓ Added rider_reply column to rider_reviews table")
        
        if 'rider_reply_at' not in columns:
            cur.execute("ALTER TABLE rider_reviews ADD COLUMN rider_reply_at DATETIME")
            print("✓ Added rider_reply_at column to rider_reviews table")
        
        conn.commit()
        print("\n✅ SQLite migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
    return True

def run_mysql():
    """Add reply columns to MySQL reviews tables"""
    import pymysql
    
    print("\n=== MySQL: Adding review reply columns ===\n")
    
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='qwerty',
            charset='utf8mb4'
        )
        cur = conn.cursor()
        
        # Check if columns exist in reviews table
        cur.execute("SHOW COLUMNS FROM reviews LIKE 'seller_reply'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE reviews ADD COLUMN seller_reply TEXT")
            print("✓ Added seller_reply column to reviews table")
        
        cur.execute("SHOW COLUMNS FROM reviews LIKE 'seller_reply_at'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE reviews ADD COLUMN seller_reply_at DATETIME")
            print("✓ Added seller_reply_at column to reviews table")
        
        # Check if columns exist in rider_reviews table
        cur.execute("SHOW COLUMNS FROM rider_reviews LIKE 'rider_reply'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE rider_reviews ADD COLUMN rider_reply TEXT")
            print("✓ Added rider_reply column to rider_reviews table")
        
        cur.execute("SHOW COLUMNS FROM rider_reviews LIKE 'rider_reply_at'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE rider_reviews ADD COLUMN rider_reply_at DATETIME")
            print("✓ Added rider_reply_at column to rider_reviews table")
        
        conn.commit()
        print("\n✅ MySQL migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
    
    return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Add review reply columns')
    parser.add_argument('--db', choices=['sqlite', 'mysql'], default='mysql',
                       help='Database type (default: mysql)')
    args = parser.parse_args()
    
    if args.db == 'sqlite':
        success = run_sqlite()
    else:
        success = run_mysql()
    
    sys.exit(0 if success else 1)
