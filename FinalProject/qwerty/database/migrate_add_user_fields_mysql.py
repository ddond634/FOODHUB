"""
Migration script to add missing user profile fields to the users table (MySQL).
This script will automatically add the required columns if they don't exist.
"""
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

def migrate():
    try:
        # Get MySQL connection details from environment
        config = {
            'host': os.environ.get('DB_HOST', '127.0.0.1'),
            'user': os.environ.get('DB_USER', 'root'),
            'password': os.environ.get('DB_PASS', ''),
            'db': os.environ.get('DB_NAME', 'qwerty'),
            'port': int(os.environ.get('DB_PORT', '3306')),
            'charset': 'utf8mb4'
        }
        
        print(f"Connecting to MySQL database: {config['db']}@{config['host']}:{config['port']}")
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # Check which columns already exist
        cursor.execute("SHOW COLUMNS FROM users")
        existing_cols = {row[0] for row in cursor.fetchall()}
        print(f"\nExisting columns ({len(existing_cols)}): {sorted(existing_cols)}")
        
        # Columns to add with their definitions
        columns_to_add = {
            'middle_name': 'VARCHAR(255) NULL',
            'suffix': 'VARCHAR(50) NULL',
            'phone': 'VARCHAR(50) NULL',
            'address_line1': 'VARCHAR(255) NULL',
            'address_line2': 'VARCHAR(255) NULL',
            'city': 'VARCHAR(100) NULL',
            'province': 'VARCHAR(100) NULL',
            'region': 'VARCHAR(100) NULL',
            'postal_code': 'VARCHAR(20) NULL',
        }
        
        added_count = 0
        for col_name, col_def in columns_to_add.items():
            if col_name not in existing_cols:
                try:
                    # MySQL 5.7+ supports IF NOT EXISTS
                    sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"
                    cursor.execute(sql)
                    print(f"✅ Added column: {col_name}")
                    added_count += 1
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'duplicate column' in error_msg or 'already exists' in error_msg:
                        print(f"⏭️  Column {col_name} already exists, skipping")
                    else:
                        print(f"❌ Error adding column {col_name}: {e}")
            else:
                print(f"⏭️  Column {col_name} already exists, skipping")
        
        conn.commit()
        print(f"\n✅ Migration complete! Added {added_count} new columns.")
        
        # Verify
        cursor.execute("SHOW COLUMNS FROM users")
        final_cols = {row[0] for row in cursor.fetchall()}
        print(f"\nFinal columns ({len(final_cols)} total): {sorted(final_cols)}")
        
        # Check required columns
        required_cols = ['middle_name', 'suffix', 'phone', 'address_line1', 'address_line2', 
                        'city', 'province', 'region', 'postal_code']
        print(f"\nRequired columns check:")
        all_exist = True
        for req_col in required_cols:
            exists = req_col in final_cols
            status = "✅ EXISTS" if exists else "❌ MISSING"
            print(f"  - {req_col}: {status}")
            if not exists:
                all_exist = False
        
        if all_exist:
            print("\n✅ All required columns are present!")
        else:
            print("\n⚠️  Some required columns are missing. Please check the errors above.")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("MySQL Migration: Add User Profile Fields")
    print("=" * 60)
    success = migrate()
    if success:
        print("\n✅ Migration successful! You can now save personal information.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
    print("=" * 60)

