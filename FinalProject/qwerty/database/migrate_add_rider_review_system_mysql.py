"""
Add status column to riders table for approval workflow
Similar to sellers table implementation
"""
import pymysql
import os
from datetime import datetime

# Database configuration
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'qwerty')
DB_PORT = int(os.getenv('DB_PORT', '3306'))

def run_migration():
    try:
        print(f"Connecting to MySQL database '{DB_NAME}'...")
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            autocommit=False
        )
        cursor = conn.cursor()
        print("✓ Connected successfully\n")
        
        # 1. Add status column if it doesn't exist
        print("1. Adding status column to riders table...")
        try:
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN status ENUM('pending', 'active', 'declined') DEFAULT 'pending'
                AFTER verified
            """)
            print("   ✓ Status column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("   ⚠ Status column already exists (skipping)")
            else:
                raise
        
        # 2. Add rejection_reason column
        print("2. Adding rejection_reason column...")
        try:
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN rejection_reason TEXT NULL
                AFTER status
            """)
            print("   ✓ Rejection_reason column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("   ⚠ Rejection_reason column already exists (skipping)")
            else:
                raise
        
        # 3. Add reviewed_by column
        print("3. Adding reviewed_by column...")
        try:
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN reviewed_by INT(11) NULL
                AFTER rejection_reason
            """)
            print("   ✓ Reviewed_by column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("   ⚠ Reviewed_by column already exists (skipping)")
            else:
                raise
        
        # 4. Add reviewed_at column
        print("4. Adding reviewed_at column...")
        try:
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN reviewed_at DATETIME NULL
                AFTER reviewed_by
            """)
            print("   ✓ Reviewed_at column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("   ⚠ Reviewed_at column already exists (skipping)")
            else:
                raise
        
        # 5. Add contact_number column
        print("5. Adding contact_number column...")
        try:
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN contact_number VARCHAR(50) NULL
                AFTER reviewed_at
            """)
            print("   ✓ Contact_number column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("   ⚠ Contact_number column already exists (skipping)")
            else:
                raise
        
        # 6. Add document_url column
        print("6. Adding document_url column...")
        try:
            cursor.execute("""
                ALTER TABLE riders 
                ADD COLUMN document_url VARCHAR(500) NULL
                AFTER contact_number
            """)
            print("   ✓ Document_url column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("   ⚠ Document_url column already exists (skipping)")
            else:
                raise
        
        # 7. Create rider_audit_log table
        print("7. Creating rider_audit_log table...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rider_audit_log (
                    id INT(11) AUTO_INCREMENT PRIMARY KEY,
                    rider_id INT(11) NOT NULL,
                    admin_id INT(11) NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    previous_status VARCHAR(50),
                    new_status VARCHAR(50),
                    reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_rider_id (rider_id),
                    INDEX idx_admin_id (admin_id),
                    INDEX idx_created_at (created_at)
                )
            """)
            print("   ✓ Rider_audit_log table created")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("   ⚠ Rider_audit_log table already exists (skipping)")
            else:
                raise
        
        # 8. Update existing riders based on verified status
        print("8. Updating existing riders...")
        cursor.execute("UPDATE riders SET status='active' WHERE verified=1")
        active_count = cursor.rowcount
        print(f"   ✓ Updated {active_count} verified rider(s) to 'active'")
        
        cursor.execute("UPDATE riders SET status='pending' WHERE verified=0")
        pending_count = cursor.rowcount
        print(f"   ✓ Updated {pending_count} unverified rider(s) to 'pending'")
        
        # Commit all changes
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n✅ Migration completed successfully at {datetime.now().isoformat()}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise

if __name__ == '__main__':
    run_migration()
