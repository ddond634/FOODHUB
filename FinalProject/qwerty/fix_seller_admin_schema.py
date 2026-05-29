#!/usr/bin/env python3
"""
Database Schema Fix: Seller Admin Panel
- Creates audit_logs table
- Adds missing_requirements column to sellers table
- Creates seller endpoints: approve, decline
"""
import pymysql
import sys
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Empty password for default MySQL setup
    'database': 'qwerty',
    'charset': 'utf8mb4'
}

def run_migration():
    """Execute database schema updates"""
    try:
        print("\n=== Starting Seller Admin Schema Migration ===\n")
        
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Phase 1: Create audit_logs table
        print("[1/2] Creating audit_logs table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                target_type ENUM('seller', 'rider', 'product', 'order', 'user') NOT NULL,
                target_id INT NOT NULL,
                action_type ENUM('warning', 'fine', 'restriction', 'ban', 'unban', 'suspend', 'unsuspend', 'refund', 'delete') NOT NULL,
                reason TEXT,
                amount DECIMAL(12,2),
                duration_days INT,
                admin_id INT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_target (target_type, target_id),
                INDEX idx_action (action_type),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB
        """)
        conn.commit()
        print("    ✓ audit_logs table created")
        
        # Phase 2: Add missing_requirements column to sellers table
        print("[2/2] Adding missing_requirements column to sellers table...")
        
        # Check if column already exists
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'qwerty' 
            AND TABLE_NAME = 'sellers' 
            AND COLUMN_NAME = 'missing_requirements'
        """)
        exists = cur.fetchone()[0] > 0
        
        if not exists:
            cur.execute("""
                ALTER TABLE sellers 
                ADD COLUMN missing_requirements TEXT AFTER verified
            """)
            conn.commit()
            print("    ✓ missing_requirements column added")
        else:
            print("    ⚠ missing_requirements column already exists, skipping")
        
        cur.close()
        conn.close()
        
        print("\n=== Migration Complete ===")
        print("✓ audit_logs table ready")
        print("✓ sellers.missing_requirements column ready")
        print("\nNext: Restart server to use new schema\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
