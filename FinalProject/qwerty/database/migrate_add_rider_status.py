"""
Migration Script: Add Rider Status Management Columns
Adds: rider_status, availability, current_location, approved_at, last_active to riders table
"""

import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

def migrate():
    # Database connection parameters
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'hub_ecommerce'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    
    try:
        # Connect to database
        print("Connecting to MySQL database...")
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        print("✅ Connected successfully!\n")
        
        # Check if rider_status column already exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'riders' 
            AND COLUMN_NAME = 'rider_status'
        """, (db_config['database'],))
        
        if cursor.fetchone():
            print("⚠️  rider_status column already exists. Skipping migration.")
            cursor.close()
            connection.close()
            return
        
        print("🔄 Starting migration: Adding rider status columns...\n")
        
        # Add rider_status column
        print("1️⃣  Adding rider_status ENUM column...")
        cursor.execute("""
            ALTER TABLE riders 
            ADD COLUMN rider_status ENUM('pending','active','suspended','offline') 
            DEFAULT 'pending' 
            AFTER verified
        """)
        print("   ✅ rider_status column added\n")
        
        # Add availability column
        print("2️⃣  Adding availability ENUM column...")
        cursor.execute("""
            ALTER TABLE riders 
            ADD COLUMN availability ENUM('available','busy','offline') 
            DEFAULT 'offline' 
            AFTER rider_status
        """)
        print("   ✅ availability column added\n")
        
        # Add current_location column
        print("3️⃣  Adding current_location column...")
        cursor.execute("""
            ALTER TABLE riders 
            ADD COLUMN current_location VARCHAR(255) 
            AFTER availability
        """)
        print("   ✅ current_location column added\n")
        
        # Add approved_at column
        print("4️⃣  Adding approved_at DATETIME column...")
        cursor.execute("""
            ALTER TABLE riders 
            ADD COLUMN approved_at DATETIME 
            AFTER current_location
        """)
        print("   ✅ approved_at column added\n")
        
        # Add last_active column
        print("5️⃣  Adding last_active DATETIME column...")
        cursor.execute("""
            ALTER TABLE riders 
            ADD COLUMN last_active DATETIME 
            AFTER approved_at
        """)
        print("   ✅ last_active column added\n")
        
        # Update existing verified riders to 'active' status
        print("6️⃣  Updating existing verified riders to 'active' status...")
        cursor.execute("""
            UPDATE riders 
            SET rider_status = 'active', 
                availability = 'offline',
                approved_at = NOW(),
                last_active = NOW()
            WHERE verified = 1
        """)
        updated_count = cursor.rowcount
        print(f"   ✅ Updated {updated_count} verified rider(s) to 'active' status\n")
        
        # Commit all changes
        connection.commit()
        print("✅ Migration completed successfully!")
        print("\n📊 Summary:")
        print(f"   - Added 5 new columns to riders table")
        print(f"   - Updated {updated_count} existing verified rider(s)")
        print(f"   - Rider status management is now active!")
        
        # Show sample data
        print("\n📋 Sample rider data:")
        cursor.execute("""
            SELECT id, verified, rider_status, availability, approved_at 
            FROM riders 
            LIMIT 3
        """)
        sample_riders = cursor.fetchall()
        
        if sample_riders:
            for rider in sample_riders:
                print(f"   Rider #{rider['id']}: verified={rider['verified']}, "
                      f"status={rider['rider_status']}, "
                      f"availability={rider['availability']}, "
                      f"approved={rider['approved_at']}")
        else:
            print("   No riders in database yet")
        
        cursor.close()
        connection.close()
        print("\n✅ Database connection closed")
        
    except pymysql.Error as e:
        print(f"\n❌ MySQL Error: {e}")
        if 'connection' in locals():
            connection.rollback()
            connection.close()
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if 'connection' in locals():
            connection.rollback()
            connection.close()
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Rider Status Migration Script")
    print("=" * 60)
    print()
    migrate()
    print()
    print("=" * 60)
    print("🎉 Migration process completed!")
    print("=" * 60)
