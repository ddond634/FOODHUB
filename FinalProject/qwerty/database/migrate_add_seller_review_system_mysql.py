"""
MySQL migration to add seller review system fields.
Adds status, rejection_reason, reviewed_by, and reviewed_at fields to sellers table.
Creates seller_audit_log table for accountability.
"""
import pymysql
import os
from datetime import datetime

# MySQL configuration
MYSQL_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'db': os.environ.get('DB_NAME', 'qwerty'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'cursorclass': pymysql.cursors.DictCursor,
}

def migrate():
    """Add seller review system fields to MySQL database."""
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("Starting seller review system migration for MySQL...")
        
        # Add status column to sellers table
        print("Adding status column to sellers table...")
        try:
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN status ENUM('pending', 'active', 'declined') 
                DEFAULT 'pending'
            """)
            print("✓ Status column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("⚠ Status column already exists, skipping...")
            else:
                raise
        
        # Add rejection_reason column
        print("Adding rejection_reason column to sellers table...")
        try:
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN rejection_reason TEXT
            """)
            print("✓ Rejection_reason column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("⚠ Rejection_reason column already exists, skipping...")
            else:
                raise
        
        # Add reviewed_by column
        print("Adding reviewed_by column to sellers table...")
        try:
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN reviewed_by INT,
                ADD FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
            """)
            print("✓ Reviewed_by column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("⚠ Reviewed_by column already exists, skipping...")
            else:
                raise
        
        # Add reviewed_at column
        print("Adding reviewed_at column to sellers table...")
        try:
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN reviewed_at DATETIME
            """)
            print("✓ Reviewed_at column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("⚠ Reviewed_at column already exists, skipping...")
            else:
                raise
        
        # Add contact_number column
        print("Adding contact_number column to sellers table...")
        try:
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN contact_number VARCHAR(50)
            """)
            print("✓ Contact_number column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("⚠ Contact_number column already exists, skipping...")
            else:
                raise
        
        # Add document_url column
        print("Adding document_url column to sellers table...")
        try:
            cursor.execute("""
                ALTER TABLE sellers 
                ADD COLUMN document_url VARCHAR(500)
            """)
            print("✓ Document_url column added")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print("⚠ Document_url column already exists, skipping...")
            else:
                raise
        
        # Create seller_audit_log table
        print("Creating seller_audit_log table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seller_audit_log (
                id INT PRIMARY KEY AUTO_INCREMENT,
                seller_id INT NOT NULL,
                admin_id INT NOT NULL,
                action VARCHAR(50) NOT NULL,
                previous_status VARCHAR(20),
                new_status VARCHAR(20),
                reason TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_seller_id (seller_id),
                INDEX idx_admin_id (admin_id)
            )
        """)
        print("✓ Seller_audit_log table created")
        
        # Update existing sellers to have 'active' status (backward compatibility)
        print("Setting existing verified sellers to 'active' status...")
        cursor.execute("""
            UPDATE sellers 
            SET status = 'active' 
            WHERE verified = 1
        """)
        affected = cursor.rowcount
        print(f"✓ Updated {affected} verified sellers to 'active'")
        
        print("Setting existing unverified sellers to 'pending' status...")
        cursor.execute("""
            UPDATE sellers 
            SET status = 'pending' 
            WHERE verified = 0 OR verified IS NULL
        """)
        affected = cursor.rowcount
        print(f"✓ Updated {affected} unverified sellers to 'pending'")
        
        conn.commit()
        print("✓ Migration completed successfully!")
        print(f"Migration completed at: {datetime.now().isoformat()}")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    migrate()
