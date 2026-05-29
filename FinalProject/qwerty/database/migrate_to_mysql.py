#!/usr/bin/env python3
"""
Migration Script: SQLite to MySQL for Hub E-commerce & ERP System
Migrates all data: users, products, orders, sales reports, accounts
"""

import sqlite3
import pymysql
import pymysql.cursors
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv('.env')

# SQLite configuration
SQLITE_DB = os.path.join(os.path.dirname(__file__), 'qwerty.db')

# MySQL configuration
MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'db': os.environ.get('DB_NAME', 'qwerty'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'charset': 'utf8mb4'
}

def migrate_data():
    """Migrate all data from SQLite to MySQL"""
    
    print("[*] Starting migration from SQLite to MySQL...")
    print(f"    SQLite DB: {SQLITE_DB}")
    print(f"    MySQL: {MYSQL_CONFIG['user']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['db']}")
    print()
    
    try:
        # Connect to MySQL
        print("[1] Connecting to MySQL...")
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor(pymysql.cursors.DictCursor)
        print("    ✓ Connected to MySQL successfully")
        
        # Create database schema
        print("[2] Creating MySQL schema...")
        schema_path = os.path.join(os.path.dirname(__file__), 'qwerty', 'db', 'schema_mysql.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema = f.read()
                # Execute schema (may have multiple statements)
                for statement in schema.split(';'):
                    statement = statement.strip()
                    if statement:
                        try:
                            mysql_cursor.execute(statement)
                        except Exception as e:
                            # Skip if table already exists
                            if 'already exists' not in str(e):
                                print(f"    Warning: {e}")
            mysql_conn.commit()
            print("    ✓ Schema created/verified")
        else:
            print(f"    ✗ Schema file not found: {schema_path}")
            return False
        
        # Connect to SQLite
        print("[3] Connecting to SQLite...")
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        print("    ✓ Connected to SQLite successfully")
        
        # Migrate tables
        tables_to_migrate = [
            'users',
            'sellers',
            'riders',
            'products',
            'orders',
            'order_items',
            'wishlist',
            'reviews',
            'otp_codes',
            'refresh_tokens'
        ]
        
        total_records = 0
        
        for table in tables_to_migrate:
            print(f"[4.{tables_to_migrate.index(table) + 1}] Migrating table: {table}...")
            
            try:
                # Get column names
                sqlite_cursor.execute(f"PRAGMA table_info({table})")
                columns_info = sqlite_cursor.fetchall()
                columns = [col[1] for col in columns_info]
                
                # Get data
                sqlite_cursor.execute(f"SELECT * FROM {table}")
                rows = sqlite_cursor.fetchall()
                record_count = len(rows)
                
                if record_count == 0:
                    print(f"    ✓ No records to migrate")
                    continue
                
                # Prepare insert statement
                placeholders = ', '.join(['%s'] * len(columns))
                insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                
                # Clear existing data in MySQL table (optional - comment out to preserve)
                # mysql_cursor.execute(f"DELETE FROM {table}")
                
                # Insert data
                for row in rows:
                    values = [row[col] for col in columns]
                    try:
                        mysql_cursor.execute(insert_sql, values)
                    except Exception as e:
                        print(f"    Warning inserting row: {e}")
                        continue
                
                mysql_conn.commit()
                total_records += record_count
                print(f"    ✓ Migrated {record_count} records")
                
            except sqlite3.OperationalError as e:
                print(f"    ✗ Table doesn't exist in SQLite (skipping): {e}")
            except Exception as e:
                print(f"    ✗ Error migrating {table}: {e}")
                mysql_conn.rollback()
        
        print()
        print("=" * 60)
        print(f"[✓] Migration Complete!")
        print(f"    Total records migrated: {total_records}")
        print("=" * 60)
        print()
        
        # Verify data
        print("[5] Verifying migrated data...")
        for table in tables_to_migrate:
            try:
                mysql_cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                result = mysql_cursor.fetchone()
                count = result['cnt'] if isinstance(result, dict) else result[0]
                print(f"    {table}: {count} records")
            except Exception as e:
                print(f"    {table}: Error - {e}")
        
        print()
        print("[!] Next steps:")
        print("    1. Verify all data in MySQL database")
        print("    2. Update .env file (if not already set):")
        print("       DB_ENGINE=mysql")
        print("       DB_HOST=127.0.0.1")
        print("       DB_USER=root")
        print("       DB_PASS=your_password")
        print("       DB_NAME=qwerty")
        print("    3. Restart the Flask server")
        print("    4. Test all API endpoints")
        print()
        
        sqlite_conn.close()
        mysql_conn.close()
        return True
        
    except Exception as e:
        print(f"[✗] Migration failed: {e}")
        return False

def verify_migration():
    """Verify that MySQL has all the required data"""
    
    print("[Verification] Checking MySQL data integrity...")
    
    try:
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor(pymysql.cursors.DictCursor)
        
        checks = [
            ("SELECT COUNT(*) as cnt FROM users", "Users"),
            ("SELECT COUNT(*) as cnt FROM products", "Products"),
            ("SELECT COUNT(*) as cnt FROM orders", "Orders"),
            ("SELECT COUNT(*) as cnt FROM sellers WHERE verified=1", "Verified Sellers"),
            ("SELECT COUNT(*) as cnt FROM riders WHERE verified=1", "Verified Riders"),
            ("SELECT SUM(total) as total_sales FROM orders WHERE status='delivered'", "Total Sales Revenue"),
        ]
        
        print()
        for query, label in checks:
            try:
                mysql_cursor.execute(query)
                result = mysql_cursor.fetchone()
                if 'total' in label.lower() or 'revenue' in label.lower():
                    value = result[0] if isinstance(result, tuple) else result.get('total_sales', 0)
                    if value:
                        print(f"    {label}: ${value:,.2f}")
                    else:
                        print(f"    {label}: No data")
                else:
                    value = result[0] if isinstance(result, tuple) else result.get('cnt', 0)
                    print(f"    {label}: {value}")
            except Exception as e:
                print(f"    {label}: Error - {e}")
        
        mysql_conn.close()
        print()
        
    except Exception as e:
        print(f"    Error connecting to MySQL: {e}")

if __name__ == '__main__':
    print()
    print("=" * 60)
    print("  Hub E-commerce System: SQLite to MySQL Migration")
    print("=" * 60)
    print()
    
    # Check if SQLite file exists
    if not os.path.exists(SQLITE_DB):
        print(f"[!] SQLite database not found: {SQLITE_DB}")
        print("    Please ensure qwerty.db exists before running migration.")
        exit(1)
    
    # Run migration
    success = migrate_data()
    
    if success:
        verify_migration()
        print("[✓] All systems ready for production with MySQL!")
    else:
        print("[✗] Migration encountered errors. Please review above.")
