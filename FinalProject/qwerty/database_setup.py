#!/usr/bin/env python3
"""
Database Setup - Consolidated database setup functions
Consolidates: setup_mysql_schema, setup_fresh_database
"""

import pymysql
import os


# Database configuration (base)
def get_db_config(db_name='qwerty'):
    """Get database configuration"""
    return {
        'host': 'localhost',
        'user': 'root',
        'password': '',  # Update if you have a password
        'database': db_name,
        'charset': 'utf8mb4'
    }


def get_admin_config():
    """Get admin connection config (no database specified)"""
    return {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'charset': 'utf8mb4'
    }


# ============================================================================
# Schema Setup Functions
# ============================================================================

def setup_schema(db_name='qwerty', schema_path='database/schema_mysql.sql'):
    """Import the MySQL schema into existing database
    
    Args:
        db_name: Database name to set up
        schema_path: Path to SQL schema file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db_config = get_db_config(db_name)
        
        # Connect to MySQL and use the database
        print("Connecting to MySQL...")
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        print(f"Using database '{db_name}'...")
        
        # Drop all tables first
        print("Dropping existing tables...")
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        for (table_name,) in tables:
            print(f"  Dropping table '{table_name}'...")
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
        
        # Read and execute schema file
        print(f"Reading schema from {schema_path}...")
        
        if not os.path.exists(schema_path):
            print(f"❌ Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Split by semicolons and execute each statement
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
        
        print(f"Executing {len(statements)} SQL statements...")
        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    cursor.execute(statement)
                    print(f"  [{i}/{len(statements)}] ✓")
                except Exception as e:
                    print(f"  [{i}/{len(statements)}] ✗ Error: {e}")
        
        conn.commit()
        print("\n✅ Schema setup completed successfully!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error setting up schema: {e}")
        return False


def create_fresh_database(db_name='qwerty_fresh', schema_path='database/schema_mysql.sql'):
    """Create a brand new database with fresh schema
    
    Args:
        db_name: Name of database to create
        schema_path: Path to SQL schema file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        admin_config = get_admin_config()
        
        print("🔧 Connecting to MySQL...")
        conn = pymysql.connect(**admin_config)
        cursor = conn.cursor()
        
        # Drop if exists (clean slate)
        print(f"🗑️  Dropping old '{db_name}' if it exists...")
        try:
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            conn.commit()
        except:
            pass
        
        print(f"✨ Creating database '{db_name}'...")
        cursor.execute(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        print("  ✓ Database created")
        
        # Switch to the new database
        cursor.execute(f"USE `{db_name}`")
        
        # Read and execute schema
        print(f"📄 Reading schema from {schema_path}...")
        
        if not os.path.exists(schema_path):
            print(f"❌ Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Split by semicolons and execute each statement
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
        
        print(f"⚙️  Executing {len(statements)} SQL statements...")
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            if statement and not statement.upper().startswith(('CREATE DATABASE', 'USE ')):
                try:
                    cursor.execute(statement)
                    print(f"  [{i}/{len(statements)}] ✓")
                    success_count += 1
                except Exception as e:
                    print(f"  [{i}/{len(statements)}] ✗ {e}")
                    error_count += 1
        
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"\n✅ Setup completed!")
        print(f"   Success: {success_count} statements")
        print(f"   Errors: {error_count} statements")
        print(f"   Tables created: {len(tables)}")
        
        if tables:
            print(f"\n📊 Tables in database:")
            for (table_name,) in tables:
                print(f"   - {table_name}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 Database '{db_name}' is ready!")
        print(f"\n📝 Next step: Update your database configuration")
        print(f"   In backend/server.py, change DB_CONFIG['database'] to: '{db_name}'")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# CLI Entry Points
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Setup Utilities')
    parser.add_argument('command', 
                        choices=['setup-schema', 'setup-fresh'],
                        help='Command to execute')
    parser.add_argument('--db-name', default=None, help='Database name')
    parser.add_argument('--schema', default='database/schema_mysql.sql', help='Path to schema file')
    
    args = parser.parse_args()
    
    if args.command == 'setup-schema':
        db_name = args.db_name or 'qwerty'
        success = setup_schema(db_name, args.schema)
        if success:
            print("\nYou can now run: python run.py")
    
    elif args.command == 'setup-fresh':
        db_name = args.db_name or 'qwerty_fresh'
        success = create_fresh_database(db_name, args.schema)
        if not success:
            print("\n⚠️  Setup failed. Please check the error messages above.")
