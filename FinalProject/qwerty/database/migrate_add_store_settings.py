"""
Migration: Add store settings columns to sellers table
Adds: store_name, store_description, store_logo, store_banner
"""
import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'qwerty'
}

def migrate():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔧 Adding store settings columns to sellers table...")
        
        # Check and add columns one by one
        columns_to_add = [
            ("store_name", "VARCHAR(255) DEFAULT NULL"),
            ("store_description", "TEXT DEFAULT NULL"),
            ("store_logo", "VARCHAR(500) DEFAULT NULL"),
            ("store_banner", "VARCHAR(500) DEFAULT NULL")
        ]
        
        for column_name, column_def in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE sellers ADD COLUMN {column_name} {column_def}")
                print(f"  ✅ Added column: {column_name}")
            except pymysql.err.OperationalError as e:
                if "Duplicate column name" in str(e):
                    print(f"  ⚠️  Column {column_name} already exists, skipping...")
                else:
                    raise
        
        conn.commit()
        
        # Verify columns exist
        cursor.execute("SHOW COLUMNS FROM sellers")
        columns = [row[0] for row in cursor.fetchall()]
        
        print("\n📊 Current sellers table columns:")
        for col in columns:
            print(f"  - {col}")
        
        print("\n✅ Migration completed successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
