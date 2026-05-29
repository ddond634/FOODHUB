"""
Database Migration: Add Resubmission Workflow Fields
Adds missing_requirements JSON field and updates status enums for declined/resubmitted states
"""

import pymysql
import json
from datetime import datetime

# Database connection settings
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Update if you have a password
    'database': 'qwerty',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def run_migration():
    """Run the migration to add resubmission fields"""
    connection = pymysql.connect(**DB_CONFIG)
    
    try:
        with connection.cursor() as cursor:
            print("🔄 Starting migration: Add resubmission workflow fields...")
            
            # 1. Update sellers table
            print("\n1️⃣ Updating sellers table...")
            
            # Add missing_requirements column
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN IF NOT EXISTS missing_requirements JSON NULL COMMENT 'JSON array of missing requirement IDs'
            """)
            print("   ✓ Added missing_requirements column to sellers")
            
            # Update shop_status enum to include declined and resubmitted
            cursor.execute("""
                ALTER TABLE sellers 
                MODIFY COLUMN shop_status ENUM('pending','active','suspended','declined','resubmitted') DEFAULT 'pending'
            """)
            print("   ✓ Updated shop_status enum (added declined, resubmitted)")
            
            # Add decline reason and date
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN IF NOT EXISTS declined_at DATETIME NULL,
                ADD COLUMN IF NOT EXISTS declined_by INT NULL,
                ADD COLUMN IF NOT EXISTS decline_reason TEXT NULL,
                ADD COLUMN IF NOT EXISTS resubmitted_at DATETIME NULL
            """)
            print("   ✓ Added decline tracking columns to sellers")
            
            # 2. Update riders table
            print("\n2️⃣ Updating riders table...")
            
            # Add missing_requirements column
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN IF NOT EXISTS missing_requirements JSON NULL COMMENT 'JSON array of missing requirement IDs'
            """)
            print("   ✓ Added missing_requirements column to riders")
            
            # Update rider_status enum to include declined and resubmitted
            cursor.execute("""
                ALTER TABLE riders 
                MODIFY COLUMN rider_status ENUM('pending','active','suspended','offline','declined','resubmitted') DEFAULT 'pending'
            """)
            print("   ✓ Updated rider_status enum (added declined, resubmitted)")
            
            # Add decline reason and date
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN IF NOT EXISTS declined_at DATETIME NULL,
                ADD COLUMN IF NOT EXISTS declined_by INT NULL,
                ADD COLUMN IF NOT EXISTS decline_reason TEXT NULL,
                ADD COLUMN IF NOT EXISTS resubmitted_at DATETIME NULL
            """)
            print("   ✓ Added decline tracking columns to riders")
            
            # 3. Create resubmission tracking table
            print("\n3️⃣ Creating resubmission tracking table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resubmissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    user_type ENUM('seller','rider') NOT NULL,
                    missing_requirements JSON NOT NULL,
                    submitted_documents JSON NULL,
                    status ENUM('pending_resubmission','submitted','approved','declined') DEFAULT 'pending_resubmission',
                    admin_notes TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    submitted_at DATETIME NULL,
                    reviewed_at DATETIME NULL,
                    reviewed_by INT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB
            """)
            print("   ✓ Created resubmissions tracking table")
            
            # 4. Create notifications table for in-platform notifications
            print("\n4️⃣ Creating notifications table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    type ENUM('info','warning','success','error') DEFAULT 'info',
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    action_url VARCHAR(512) NULL,
                    is_read TINYINT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_read (user_id, is_read),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB
            """)
            print("   ✓ Created notifications table")
            
            # Commit changes
            connection.commit()
            print("\n✅ Migration completed successfully!")
            print("\n📊 Summary:")
            print("   • Added missing_requirements (JSON) to sellers and riders")
            print("   • Updated status enums to include 'declined' and 'resubmitted'")
            print("   • Added decline tracking fields (declined_at, declined_by, decline_reason)")
            print("   • Created resubmissions tracking table")
            print("   • Created notifications table for in-platform alerts")
            
    except Exception as e:
        connection.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        raise
    finally:
        connection.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION: Resubmission Workflow")
    print("=" * 60)
    run_migration()
