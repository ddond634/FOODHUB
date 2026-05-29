#!/usr/bin/env python3
"""
Migration: Add verification_documents table for seller and rider document uploads
"""
import pymysql
import sys
from datetime import datetime

def migrate():
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='qwerty',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        print("[1/3] Creating verification_documents table...")
        
        # Create verification documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                user_type ENUM('seller', 'rider') NOT NULL,
                document_type VARCHAR(100) NOT NULL,
                file_path VARCHAR(512) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                admin_notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user_type (user_id, user_type),
                INDEX idx_status (status)
            ) ENGINE=InnoDB
        """)
        print("  ✓ verification_documents table created")
        
        print("\n[2/3] Adding document columns to sellers table...")
        
        # Check if columns exist before adding
        cursor.execute("SHOW COLUMNS FROM sellers LIKE 'business_permit'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE sellers
                ADD COLUMN business_permit VARCHAR(512) AFTER category,
                ADD COLUMN valid_id VARCHAR(512) AFTER business_permit,
                ADD COLUMN address_proof VARCHAR(512) AFTER valid_id,
                ADD COLUMN business_logo VARCHAR(512) AFTER address_proof
            """)
            print("  ✓ Document columns added to sellers table")
        else:
            print("  ℹ Document columns already exist in sellers table")
        
        print("\n[3/3] Adding document columns to riders table...")
        
        # Check if columns exist before adding
        cursor.execute("SHOW COLUMNS FROM riders LIKE 'valid_id'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE riders
                ADD COLUMN valid_id VARCHAR(512) AFTER driver_license,
                ADD COLUMN vehicle_or_cr VARCHAR(512) AFTER valid_id,
                ADD COLUMN profile_photo VARCHAR(512) AFTER vehicle_or_cr
            """)
            print("  ✓ Document columns added to riders table")
        else:
            print("  ℹ Document columns already exist in riders table")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Migration complete!")
        print("   - verification_documents table created")
        print("   - Seller document columns: business_permit, valid_id, address_proof, business_logo")
        print("   - Rider document columns: valid_id, vehicle_or_cr, profile_photo")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
