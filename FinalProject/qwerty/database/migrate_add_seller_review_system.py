"""
Database migration to add seller review system fields.
Adds status, rejection_reason, reviewed_by, and reviewed_at fields to sellers table.
Creates seller_audit_log table for accountability.
"""
import sqlite3
from datetime import datetime

def migrate():
    """Add seller review system fields to database."""
    import os
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, 'hub.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Starting seller review system migration...")
        
        # Add new columns to sellers table
        print("Adding status column to sellers table...")
        cursor.execute("""
            ALTER TABLE sellers ADD COLUMN status TEXT 
            CHECK(status IN ('pending', 'active', 'declined')) 
            DEFAULT 'pending'
        """)
        
        print("Adding rejection_reason column to sellers table...")
        cursor.execute("""
            ALTER TABLE sellers ADD COLUMN rejection_reason TEXT
        """)
        
        print("Adding reviewed_by column to sellers table...")
        cursor.execute("""
            ALTER TABLE sellers ADD COLUMN reviewed_by INTEGER
        """)
        
        print("Adding reviewed_at column to sellers table...")
        cursor.execute("""
            ALTER TABLE sellers ADD COLUMN reviewed_at TEXT
        """)
        
        print("Adding contact_number column to sellers table...")
        cursor.execute("""
            ALTER TABLE sellers ADD COLUMN contact_number TEXT
        """)
        
        print("Adding document_url column to sellers table...")
        cursor.execute("""
            ALTER TABLE sellers ADD COLUMN document_url TEXT
        """)
        
        # Create seller_audit_log table
        print("Creating seller_audit_log table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seller_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                previous_status TEXT,
                new_status TEXT,
                reason TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(seller_id) REFERENCES sellers(id) ON DELETE CASCADE,
                FOREIGN KEY(admin_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        
        # Update existing sellers to have 'active' status (backward compatibility)
        print("Setting existing verified sellers to 'active' status...")
        cursor.execute("""
            UPDATE sellers 
            SET status = 'active' 
            WHERE verified = 1
        """)
        
        print("Setting existing unverified sellers to 'pending' status...")
        cursor.execute("""
            UPDATE sellers 
            SET status = 'pending' 
            WHERE verified = 0 OR verified IS NULL
        """)
        
        conn.commit()
        print("✓ Migration completed successfully!")
        print(f"Migration completed at: {datetime.now().isoformat()}")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"⚠ Column already exists: {e}")
            print("Migration may have already been run. Skipping...")
        else:
            print(f"✗ Migration failed: {e}")
            conn.rollback()
            raise
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
