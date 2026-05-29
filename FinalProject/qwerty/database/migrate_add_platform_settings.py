"""
Migration: Create platform_settings table
Stores platform-wide configuration like platform name, commission rates, etc.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def migrate():
    try:
        if DB_ENGINE == 'mysql':
            import pymysql
            conn = pymysql.connect(
                host=os.environ.get('DB_HOST', '127.0.0.1'),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASS', ''),
                db=os.environ.get('DB_NAME', 'qwerty'),
                port=int(os.environ.get('DB_PORT', '3306'))
            )
            cursor = conn.cursor()
            
            print("🔧 Creating platform_settings table...")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    setting_key VARCHAR(100) UNIQUE NOT NULL,
                    setting_value TEXT,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    updated_by INT,
                    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # Insert default settings
            default_settings = [
                ('platform_name', 'Hub', 'Platform name displayed throughout the application'),
                ('default_commission', '10', 'Default commission percentage for sellers'),
                ('rider_service_fee', '5', 'Service fee percentage for riders'),
                ('seller_approval_required', '1', 'Whether seller approval is required (1=yes, 0=no)')
            ]
            
            for key, value, desc in default_settings:
                cursor.execute("""
                    INSERT INTO platform_settings (setting_key, setting_value, description)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
                """, (key, value, desc))
            
            conn.commit()
            print("  ✅ platform_settings table created with default values")
            
        else:
            import sqlite3
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(BASE_DIR, 'qwerty.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            print("🔧 Creating platform_settings table...")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS platform_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    description TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER,
                    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            
            # Insert default settings
            default_settings = [
                ('platform_name', 'Hub', 'Platform name displayed throughout the application'),
                ('default_commission', '10', 'Default commission percentage for sellers'),
                ('rider_service_fee', '5', 'Service fee percentage for riders'),
                ('seller_approval_required', '1', 'Whether seller approval is required (1=yes, 0=no)')
            ]
            
            for key, value, desc in default_settings:
                cursor.execute("""
                    INSERT OR REPLACE INTO platform_settings (setting_key, setting_value, description)
                    VALUES (?, ?, ?)
                """, (key, value, desc))
            
            conn.commit()
            print("  ✅ platform_settings table created with default values")
        
        cursor.close()
        conn.close()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate()

