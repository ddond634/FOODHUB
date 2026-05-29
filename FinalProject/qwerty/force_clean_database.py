"""Force clean and recreate MySQL database"""
import pymysql
import os

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Update if you have a password
    'charset': 'utf8mb4'
}

def force_clean_database():
    """Force clean and recreate the database"""
    try:
        db_name = 'qwerty'
        
        print("🔧 Connecting to MySQL...")
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print(f"🗑️  Force dropping database '{db_name}'...")
        
        # Try to drop the database
        try:
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            conn.commit()
            print("  ✓ Database dropped")
        except Exception as e:
            print(f"  ⚠️  Warning: {e}")
        
        print(f"✨ Creating fresh database '{db_name}'...")
        cursor.execute(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        print("  ✓ Database created")
        
        # Switch to the new database
        cursor.execute(f"USE `{db_name}`")
        
        # Read and execute schema
        schema_path = 'database/schema_mysql.sql'
        print(f"📄 Reading schema from {schema_path}...")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Split by semicolons and execute each statement
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
        
        print(f"⚙️  Executing {len(statements)} SQL statements...")
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            if statement:
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
        print(f"\nYou can now run: python run.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"\nIf the error persists:")
        print(f"1. Open phpMyAdmin or MySQL Workbench")
        print(f"2. Manually drop the 'qwerty' database")
        print(f"3. Run this script again")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("  Force Clean MySQL Database")
    print("=" * 60)
    print()
    
    success = force_clean_database()
    
    if not success:
        print("\n⚠️  Setup failed. Please check the error messages above.")
