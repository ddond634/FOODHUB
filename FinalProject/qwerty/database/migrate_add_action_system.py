#!/usr/bin/env python3
"""
Migration: Add Action System
Creates audit_logs table and adds disciplinary action columns to sellers and riders tables
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    """Add action system tables and columns"""
    connection = pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'qwerty'),
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with connection.cursor() as cursor:
            print("Starting action system migration...")
            
            # Create audit_logs table
            print("Creating audit_logs table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    target_type ENUM('seller', 'rider') NOT NULL,
                    target_id INT NOT NULL,
                    action_type VARCHAR(100) NOT NULL,
                    reason TEXT,
                    amount DECIMAL(10, 2) DEFAULT NULL,
                    duration_days INT DEFAULT NULL,
                    admin_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_target (target_type, target_id),
                    INDEX idx_created_at (created_at),
                    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            print("✓ audit_logs table created")
            
            # Add columns to sellers table
            print("Adding action columns to sellers table...")
            
            # Check and add suspended_until
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'sellers' AND COLUMN_NAME = 'suspended_until'
            """, (os.getenv('DB_NAME', 'qwerty'),))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("ALTER TABLE sellers ADD COLUMN suspended_until DATETIME DEFAULT NULL")
                print("✓ Added suspended_until to sellers")
            else:
                print("  suspended_until already exists in sellers")
            
            # Check and add warning_count
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'sellers' AND COLUMN_NAME = 'warning_count'
            """, (os.getenv('DB_NAME', 'qwerty'),))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("ALTER TABLE sellers ADD COLUMN warning_count INT DEFAULT 0")
                print("✓ Added warning_count to sellers")
            else:
                print("  warning_count already exists in sellers")
            
            # Check and add restriction_level
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'sellers' AND COLUMN_NAME = 'restriction_level'
            """, (os.getenv('DB_NAME', 'qwerty'),))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("ALTER TABLE sellers ADD COLUMN restriction_level INT DEFAULT 0")
                print("✓ Added restriction_level to sellers")
            else:
                print("  restriction_level already exists in sellers")
            
            # Check and add total_fines
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'sellers' AND COLUMN_NAME = 'total_fines'
            """, (os.getenv('DB_NAME', 'qwerty'),))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("ALTER TABLE sellers ADD COLUMN total_fines DECIMAL(10, 2) DEFAULT 0.00")
                print("✓ Added total_fines to sellers")
            else:
                print("  total_fines already exists in sellers")
            
            # Add is_active column to users if not exists
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'is_active'
            """, (os.getenv('DB_NAME', 'qwerty'),))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("ALTER TABLE users ADD COLUMN is_active TINYINT(1) DEFAULT 1")
                print("✓ Added is_active to users")
            else:
                print("  is_active already exists in users")
            
            # Add columns to riders table
            print("Adding action columns to riders table...")
            
            # Check and add suspended_until
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'riders' AND COLUMN_NAME = 'suspended_until'
            """, (os.getenv('DB_NAME', 'qwerty'),))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("ALTER TABLE riders ADD COLUMN suspended_until DATETIME DEFAULT NULL")
                print("✓ Added suspended_until to riders")
            else:
                print("  suspended_until already exists in riders")
            
            # Check and add cooldown_until
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'riders' AND COLUMN_NAME = 'cooldown_until'
            """, (os.getenv('DB_NAME', 'qwerty'),))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("ALTER TABLE riders ADD COLUMN cooldown_until DATETIME DEFAULT NULL")
                print("✓ Added cooldown_until to riders")
            else:
                print("  cooldown_until already exists in riders")
            
            # Check and add warning_count
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'riders' AND COLUMN_NAME = 'warning_count'
            """, (os.getenv('DB_NAME', 'qwerty'),))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("ALTER TABLE riders ADD COLUMN warning_count INT DEFAULT 0")
                print("✓ Added warning_count to riders")
            else:
                print("  warning_count already exists in riders")
            
            # Check and add earnings_deducted
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'riders' AND COLUMN_NAME = 'earnings_deducted'
            """, (os.getenv('DB_NAME', 'qwerty'),))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("ALTER TABLE riders ADD COLUMN earnings_deducted DECIMAL(10, 2) DEFAULT 0.00")
                print("✓ Added earnings_deducted to riders")
            else:
                print("  earnings_deducted already exists in riders")
            
            # Commit all changes
            connection.commit()
            print("\n✅ Migration completed successfully!")
            print("\nNew capabilities:")
            print("  • Audit logging for all admin actions")
            print("  • Seller warnings, suspensions, fines, restrictions, and bans")
            print("  • Rider warnings, suspensions, cooldowns, earnings deductions, and bans")
            print("  • Complete action history tracking")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        connection.rollback()
        raise
    finally:
        connection.close()

if __name__ == '__main__':
    migrate()
