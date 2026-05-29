"""
Migration Script: Add Suspension Tracking Fields
Adds: suspended_at, suspended_by, suspension_reason, suspension_type to sellers and riders tables
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
        'password': os.getenv('DB_PASS', ''),
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
        
        print("=" * 70)
        print("🔒 ADDING SUSPENSION TRACKING FIELDS")
        print("=" * 70)
        print()
        
        # ===== SELLERS TABLE =====
        print("📋 SELLERS TABLE:")
        print("-" * 70)
        
        # Check if suspended_at column exists in sellers
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'sellers' 
            AND COLUMN_NAME = 'suspended_at'
        """, (db_config['database'],))
        
        if cursor.fetchone():
            print("⚠️  Suspension fields already exist in sellers table. Skipping...")
        else:
            print("1️⃣  Adding suspended_at DATETIME column...")
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN suspended_at DATETIME 
                AFTER approved_at
            """)
            print("   ✅ suspended_at column added")
            
            print("2️⃣  Adding suspended_by INT column...")
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN suspended_by INT 
                AFTER suspended_at
            """)
            cursor.execute("""
                ALTER TABLE sellers 
                ADD CONSTRAINT fk_sellers_suspended_by 
                FOREIGN KEY (suspended_by) REFERENCES users(id) 
                ON DELETE SET NULL
            """)
            print("   ✅ suspended_by column added with foreign key")
            
            print("3️⃣  Adding suspension_reason TEXT column...")
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN suspension_reason TEXT 
                AFTER suspended_by
            """)
            print("   ✅ suspension_reason column added")
            
            print("4️⃣  Adding suspension_type ENUM column...")
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN suspension_type ENUM('temporary','permanent') 
                AFTER suspension_reason
            """)
            print("   ✅ suspension_type column added")
            print("✅ Sellers table migration complete!\n")
        
        # ===== RIDERS TABLE =====
        print("📋 RIDERS TABLE:")
        print("-" * 70)
        
        # Check if suspended_at column exists in riders
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'riders' 
            AND COLUMN_NAME = 'suspended_at'
        """, (db_config['database'],))
        
        if cursor.fetchone():
            print("⚠️  Suspension fields already exist in riders table. Skipping...")
        else:
            print("1️⃣  Adding suspended_at DATETIME column...")
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN suspended_at DATETIME 
                AFTER last_active
            """)
            print("   ✅ suspended_at column added")
            
            print("2️⃣  Adding suspended_by INT column...")
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN suspended_by INT 
                AFTER suspended_at
            """)
            cursor.execute("""
                ALTER TABLE riders 
                ADD CONSTRAINT fk_riders_suspended_by 
                FOREIGN KEY (suspended_by) REFERENCES users(id) 
                ON DELETE SET NULL
            """)
            print("   ✅ suspended_by column added with foreign key")
            
            print("3️⃣  Adding suspension_reason TEXT column...")
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN suspension_reason TEXT 
                AFTER suspended_by
            """)
            print("   ✅ suspension_reason column added")
            
            print("4️⃣  Adding suspension_type ENUM column...")
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN suspension_type ENUM('temporary','permanent') 
                AFTER suspension_reason
            """)
            print("   ✅ suspension_type column added")
            print("✅ Riders table migration complete!\n")
        
        # Commit all changes
        connection.commit()
        
        print("=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("📊 Summary:")
        print("   - Added 4 suspension tracking columns to sellers table")
        print("   - Added 4 suspension tracking columns to riders table")
        print("   - Total: 8 new columns across 2 tables")
        print()
        print("🔒 New Suspension Fields:")
        print("   • suspended_at: Timestamp of suspension")
        print("   • suspended_by: Admin user ID who suspended the account")
        print("   • suspension_reason: Detailed reason for suspension")
        print("   • suspension_type: 'temporary' or 'permanent'")
        print()
        
        # Show sample data structure
        print("📋 Verification - Sellers table structure:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'sellers'
            AND COLUMN_NAME LIKE '%%suspend%%'
            ORDER BY ORDINAL_POSITION
        """, (db_config['database'],))
        
        seller_cols = cursor.fetchall()
        if seller_cols:
            for col in seller_cols:
                print(f"   • {col['COLUMN_NAME']}: {col['COLUMN_TYPE']}")
        else:
            print("   No suspension columns found (migration may have been skipped)")
        
        print()
        print("📋 Verification - Riders table structure:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'riders'
            AND COLUMN_NAME LIKE '%%suspend%%'
            ORDER BY ORDINAL_POSITION
        """, (db_config['database'],))
        
        rider_cols = cursor.fetchall()
        if rider_cols:
            for col in rider_cols:
                print(f"   • {col['COLUMN_NAME']}: {col['COLUMN_TYPE']}")
        else:
            print("   No suspension columns found (migration may have been skipped)")
        
        cursor.close()
        connection.close()
        print()
        print("✅ Database connection closed")
        print()
        print("🎯 Next Steps:")
        print("   1. Suspension system is now active")
        print("   2. Admins can suspend/reactivate sellers and riders")
        print("   3. Suspensions take effect instantly across the system")
        print("   4. All suspension actions are tracked with admin ID and reason")
        
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
    print()
    print("=" * 70)
    print("🚀 SUSPENSION SYSTEM MIGRATION")
    print("=" * 70)
    print()
    migrate()
    print()
    print("=" * 70)
    print("🎉 MIGRATION PROCESS COMPLETED!")
    print("=" * 70)
    print()
