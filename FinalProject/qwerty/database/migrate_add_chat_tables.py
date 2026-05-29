"""
Migration Script: Add Chat Feature Tables
Adds: conversations and messages tables for customer-to-seller chat
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
        print("💬 ADDING CHAT FEATURE TABLES")
        print("=" * 70)
        print()
        
        # Check if conversations table exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'conversations'
        """, (db_config['database'],))
        
        result = cursor.fetchone()
        
        if result['count'] > 0:
            print("⚠️  Chat tables already exist. Skipping migration...")
        else:
            # Create conversations table
            print("1️⃣  Creating conversations table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    customer_id INT NOT NULL,
                    seller_id INT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_conversation (customer_id, seller_id),
                    INDEX idx_customer (customer_id),
                    INDEX idx_seller (seller_id)
                ) ENGINE=InnoDB
            """)
            print("   ✅ conversations table created")
            print("      - customer_id: INT (FK to users)")
            print("      - seller_id: INT (FK to users)")
            print("      - created_at: DATETIME")
            print("      - updated_at: DATETIME (auto-update)")
            print("      - Unique constraint: (customer_id, seller_id)")
            print()
            
            # Create messages table
            print("2️⃣  Creating messages table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    conversation_id INT NOT NULL,
                    sender_id INT NOT NULL,
                    sender_type ENUM('customer','seller') NOT NULL,
                    message TEXT NOT NULL,
                    is_read TINYINT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_conversation (conversation_id),
                    INDEX idx_sender (sender_id),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB
            """)
            print("   ✅ messages table created")
            print("      - conversation_id: INT (FK to conversations)")
            print("      - sender_id: INT (FK to users)")
            print("      - sender_type: ENUM('customer','seller')")
            print("      - message: TEXT")
            print("      - is_read: TINYINT (0 or 1)")
            print("      - created_at: DATETIME")
            print()
        
        # Commit all changes
        connection.commit()
        
        print("=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("📊 Summary:")
        print("   - conversations table: Stores customer-seller chat sessions")
        print("   - messages table: Stores individual chat messages")
        print("   - Unique conversation per customer-seller pair")
        print("   - Messages support read status tracking")
        print("   - Optimized with indexes for fast queries")
        print()
        
        # Show table structures
        print("📋 Verification - conversations table:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'conversations'
            ORDER BY ORDINAL_POSITION
        """, (db_config['database'],))
        
        conv_cols = cursor.fetchall()
        if conv_cols:
            for col in conv_cols:
                key_info = f" [{col['COLUMN_KEY']}]" if col['COLUMN_KEY'] else ""
                print(f"   • {col['COLUMN_NAME']}: {col['COLUMN_TYPE']}{key_info}")
        
        print()
        print("📋 Verification - messages table:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'messages'
            ORDER BY ORDINAL_POSITION
        """, (db_config['database'],))
        
        msg_cols = cursor.fetchall()
        if msg_cols:
            for col in msg_cols:
                key_info = f" [{col['COLUMN_KEY']}]" if col['COLUMN_KEY'] else ""
                print(f"   • {col['COLUMN_NAME']}: {col['COLUMN_TYPE']}{key_info}")
        
        cursor.close()
        connection.close()
        print()
        print("✅ Database connection closed")
        print()
        print("🎯 Next Steps:")
        print("   1. Chat feature is now active")
        print("   2. Customers can message sellers")
        print("   3. Sellers can reply to customers")
        print("   4. Conversations auto-created on first message")
        print("   5. Messages load chronologically")
        print("   6. Read status tracking enabled")
        
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
    print("🚀 CHAT FEATURE MIGRATION")
    print("=" * 70)
    print()
    migrate()
    print()
    print("=" * 70)
    print("🎉 MIGRATION PROCESS COMPLETED!")
    print("=" * 70)
    print()
