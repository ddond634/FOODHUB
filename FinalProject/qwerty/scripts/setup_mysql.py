"""
MySQL Database Setup Script for Hub E-Commerce System

This script will:
1. Create the MySQL database if it doesn't exist
2. Import the schema from schema_mysql.sql
3. Verify the setup

Prerequisites:
- MySQL server running (XAMPP, standalone MySQL, etc.)
- Update .env file with your MySQL credentials
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# MySQL configuration from .env
MYSQL_HOST = os.environ.get('DB_HOST', '127.0.0.1')
MYSQL_USER = os.environ.get('DB_USER', 'root')
MYSQL_PASS = os.environ.get('DB_PASS', '')
MYSQL_DB = os.environ.get('DB_NAME', 'qwerty')
MYSQL_PORT = int(os.environ.get('DB_PORT', '3306'))

def create_database():
    """Create the database if it doesn't exist"""
    print(f"Connecting to MySQL server at {MYSQL_HOST}:{MYSQL_PORT}...")
    
    try:
        # Connect without database to create it
        conn = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASS,
            port=MYSQL_PORT,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # Create database
        print(f"Creating database '{MYSQL_DB}' if it doesn't exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print(f"✓ Database '{MYSQL_DB}' is ready")
        
        cursor.close()
        conn.close()
        return True
        
    except pymysql.Error as e:
        print(f"✗ Error creating database: {e}")
        return False

def import_schema():
    """Import schema from schema_mysql.sql"""
    schema_path = os.path.join(os.path.dirname(BASE_DIR), 'database', 'schema_mysql.sql')
    
    if not os.path.exists(schema_path):
        print(f"✗ Schema file not found: {schema_path}")
        return False
    
    print(f"\nImporting schema from {schema_path}...")
    
    try:
        # Connect to the database
        conn = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASS,
            db=MYSQL_DB,
            port=MYSQL_PORT,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # Read and execute schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Split by semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement and not statement.startswith('--'):
                cursor.execute(statement)
        
        conn.commit()
        print("✓ Schema imported successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except pymysql.Error as e:
        print(f"✗ Error importing schema: {e}")
        return False

def verify_setup():
    """Verify that all tables were created"""
    print("\nVerifying database setup...")
    
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASS,
            db=MYSQL_DB,
            port=MYSQL_PORT,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SHOW TABLES;")
        tables = [table[0] for table in cursor.fetchall()]
        
        expected_tables = [
            'users', 'sellers', 'riders', 'suppliers', 'products',
            'inventory_movements', 'orders', 'order_items',
            'purchase_orders', 'purchase_order_items',
            'refresh_tokens', 'wishlist'
        ]
        
        print(f"\nFound {len(tables)} tables:")
        for table in tables:
            status = "✓" if table in expected_tables else "?"
            print(f"  {status} {table}")
        
        missing_tables = [t for t in expected_tables if t not in tables]
        if missing_tables:
            print(f"\n⚠ Missing tables: {', '.join(missing_tables)}")
        else:
            print("\n✓ All expected tables are present")
        
        cursor.close()
        conn.close()
        return len(missing_tables) == 0
        
    except pymysql.Error as e:
        print(f"✗ Error verifying setup: {e}")
        return False

def main():
    """Main setup function"""
    print("=" * 60)
    print("  Hub E-Commerce MySQL Database Setup")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Host: {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"  User: {MYSQL_USER}")
    print(f"  Database: {MYSQL_DB}")
    print(f"  Password: {'(set)' if MYSQL_PASS else '(empty)'}")
    print()
    
    # Step 1: Create database
    if not create_database():
        print("\n✗ Setup failed at database creation")
        return False
    
    # Step 2: Import schema
    if not import_schema():
        print("\n✗ Setup failed at schema import")
        return False
    
    # Step 3: Verify setup
    if not verify_setup():
        print("\n⚠ Setup completed with warnings")
        return True
    
    print("\n" + "=" * 60)
    print("✓ MySQL database setup completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Verify .env has DB_ENGINE=mysql")
    print("2. Run: python backend/run_server.py")
    print("3. Access the application at http://127.0.0.1:5000")
    print()
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        exit(1)
