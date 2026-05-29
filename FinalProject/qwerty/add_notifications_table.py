#!/usr/bin/env python3
"""
Database Schema Fix: Add notifications table
"""
import pymysql
import sys

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'qwerty',
    'charset': 'utf8mb4'
}

def run_migration():
    """Create notifications table"""
    try:
        print("\n=== Adding notifications table ===\n")
        
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                body TEXT,
                `read` TINYINT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user (user_id),
                INDEX idx_read (user_id, `read`)
            ) ENGINE=InnoDB
        """)
        conn.commit()
        print("✓ notifications table created")
        
        cur.close()
        conn.close()
        
        print("\nMigration complete!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
