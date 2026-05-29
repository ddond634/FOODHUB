"""
Migration script to add missing user profile fields to the users table.
Adds: middle_name, suffix, phone, address_line1, address_line2, city, province, region, postal_code
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'qwerty.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check which columns already exist
        cursor.execute("PRAGMA table_info(users)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        print(f"Existing columns: {sorted(existing_cols)}")
        
        # Columns to add
        columns_to_add = [
            ('middle_name', 'TEXT'),
            ('suffix', 'TEXT'),
            ('phone', 'TEXT'),
            ('address_line1', 'TEXT'),
            ('address_line2', 'TEXT'),
            ('city', 'TEXT'),
            ('province', 'TEXT'),
            ('region', 'TEXT'),
            ('postal_code', 'TEXT'),
        ]
        
        added_count = 0
        for col_name, col_type in columns_to_add:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    print(f"✅ Added column: {col_name}")
                    added_count += 1
                except Exception as e:
                    print(f"❌ Error adding column {col_name}: {e}")
            else:
                print(f"⏭️  Column {col_name} already exists, skipping")
        
        conn.commit()
        print(f"\n✅ Migration complete! Added {added_count} new columns.")
        
        # Verify
        cursor.execute("PRAGMA table_info(users)")
        final_cols = {row[1] for row in cursor.fetchall()}
        print(f"\nFinal columns ({len(final_cols)} total): {sorted(final_cols)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    print("Running migration to add user profile fields...")
    print(f"Database: {DB_PATH}\n")
    success = migrate()
    if success:
        print("\n✅ Migration successful! You can now save personal information.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")

