"""
Migration: Add messaging system tables
Creates conversations and messages tables for customer-seller communication
"""

import os
import sys
import pymysql

DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

def get_connection():
    """Get database connection without Flask context"""
    if DB_ENGINE == 'mysql':
        return pymysql.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', ''),
            database=os.environ.get('DB_NAME', 'qwerty'),
            port=int(os.environ.get('DB_PORT', 3306))
        )
    else:
        import sqlite3
        return sqlite3.connect('qwerty.db')

def migrate():
    """Create conversations and messages tables"""
    print("🔄 Starting migration: Add Messaging System")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if DB_ENGINE == 'mysql':
            # Create conversations table
            print("📝 Creating conversations table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    customer_id INT NOT NULL,
                    seller_id INT NOT NULL,
                    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_conversation (customer_id, seller_id),
                    INDEX idx_customer_id (customer_id),
                    INDEX idx_seller_id (seller_id),
                    INDEX idx_last_message_at (last_message_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Create messages table
            print("📝 Creating messages table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    conversation_id INT NOT NULL,
                    sender_id INT NOT NULL,
                    sender_role ENUM('customer', 'seller') NOT NULL,
                    message_text TEXT NOT NULL,
                    read_status BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    INDEX idx_conversation_id (conversation_id),
                    INDEX idx_sender_id (sender_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_read_status (read_status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
        else:  # SQLite
            # Create conversations table
            print("📝 Creating conversations table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    seller_id INTEGER NOT NULL,
                    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (seller_id) REFERENCES sellers(id) ON DELETE CASCADE,
                    UNIQUE (customer_id, seller_id)
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_customer_id ON conversations(customer_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_seller_id ON conversations(seller_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_message_at ON conversations(last_message_at)')
            
            # Create messages table
            print("📝 Creating messages table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    sender_id INTEGER NOT NULL,
                    sender_role TEXT NOT NULL CHECK(sender_role IN ('customer', 'seller')),
                    message_text TEXT NOT NULL,
                    read_status BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_id ON messages(conversation_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sender_id ON messages(sender_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON messages(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_read_status ON messages(read_status)')
        
        conn.commit()
        print("✅ Conversations table created successfully")
        print("✅ Messages table created successfully")
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
