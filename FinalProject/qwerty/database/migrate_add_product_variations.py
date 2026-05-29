"""
Migration: Add Product Variations System

This migration creates tables to support product variations (size, flavor, etc.)
Allows multiple variations per product with individual pricing and inventory.
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'db': os.environ.get('DB_NAME', 'qwerty'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'charset': 'utf8mb4'
}

def run_migration():
    """Execute the migration"""
    try:
        print("Connecting to MySQL database...")
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n=== Creating Product Variations Tables ===\n")
        
        # 1. Create product_variation_options table (defines available variation types)
        print("1. Creating product_variation_options table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_variation_options (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT NOT NULL,
                variation_type VARCHAR(50) NOT NULL COMMENT 'e.g., Size, Flavor, Color',
                variation_value VARCHAR(100) NOT NULL COMMENT 'e.g., Small, Chocolate, Red',
                price_adjustment DECIMAL(12,2) DEFAULT 0.00 COMMENT 'Additional cost for this variation',
                stock INT DEFAULT 0,
                sku VARCHAR(100) UNIQUE COMMENT 'Stock Keeping Unit for this variation',
                is_available TINYINT DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                INDEX idx_product_variation (product_id, variation_type),
                INDEX idx_sku (sku)
            ) ENGINE=InnoDB COMMENT='Stores individual product variations with pricing and inventory';
        """)
        print("   ✓ product_variation_options table created")
        
        # 2. Update order_items to support variations
        print("\n2. Adding variation support to order_items...")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'order_items' 
            AND COLUMN_NAME = 'variation_id'
        """, (DB_CONFIG['db'],))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE order_items 
                ADD COLUMN variation_id INT DEFAULT NULL AFTER product_id,
                ADD COLUMN variation_details TEXT COMMENT 'JSON string of selected variations',
                ADD FOREIGN KEY (variation_id) REFERENCES product_variation_options(id) ON DELETE SET NULL
            """)
            print("   ✓ Added variation_id and variation_details columns to order_items")
        else:
            print("   ⚠ Columns already exist, skipping...")
        
        # 3. Create cart_items table for persistent cart
        print("\n3. Creating cart_items table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_id INT NOT NULL,
                variation_id INT DEFAULT NULL,
                quantity INT DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                FOREIGN KEY (variation_id) REFERENCES product_variation_options(id) ON DELETE CASCADE,
                UNIQUE KEY unique_cart_item (user_id, product_id, variation_id),
                INDEX idx_user_cart (user_id)
            ) ENGINE=InnoDB COMMENT='Stores user cart items with variation support';
        """)
        print("   ✓ cart_items table created")
        
        # 4. Create inventory_movements_variations table
        print("\n4. Creating inventory_movements_variations table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_movements_variations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                variation_id INT NOT NULL,
                qty INT NOT NULL,
                movement_type ENUM('sale','purchase','adjustment','return') NOT NULL,
                ref VARCHAR(255) COMMENT 'Reference: order_id, po_id, etc.',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (variation_id) REFERENCES product_variation_options(id) ON DELETE CASCADE,
                INDEX idx_variation_movements (variation_id, created_at)
            ) ENGINE=InnoDB COMMENT='Tracks inventory movements for product variations';
        """)
        print("   ✓ inventory_movements_variations table created")
        
        conn.commit()
        
        # Verification
        print("\n=== Verifying Migration ===\n")
        
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_COMMENT 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME IN ('product_variation_options', 'cart_items', 'inventory_movements_variations')
            ORDER BY TABLE_NAME
        """, (DB_CONFIG['db'],))
        
        tables = cursor.fetchall()
        print("Created tables:")
        for table in tables:
            print(f"  ✓ {table[0]}: {table[1]}")
        
        # Show product_variation_options structure
        print("\n=== product_variation_options structure ===")
        cursor.execute("DESCRIBE product_variation_options")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} {row[2]} {row[3]}")
        
        # Show order_items updated structure
        print("\n=== order_items updated columns ===")
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'order_items'
            AND COLUMN_NAME IN ('variation_id', 'variation_details')
        """, (DB_CONFIG['db'],))
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} (Nullable: {row[2]}) - {row[3]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("  1. Sellers can now add variations to products via API")
        print("  2. Customers can select variations when adding to cart")
        print("  3. Inventory is tracked per variation")
        print("  4. Orders include variation details")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    run_migration()
