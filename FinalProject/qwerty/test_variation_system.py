"""
Test script to verify product variation system is working
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'db': os.environ.get('DB_NAME', 'qwerty'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'charset': 'utf8mb4'
}

def test_variation_system():
    """Test the variation system"""
    print("\n=== Testing Product Variation System ===\n")
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. Check if product_variation_options table exists
        print("1. Checking if product_variation_options table exists...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'product_variation_options'
        """, (DB_CONFIG['db'],))
        
        if cursor.fetchone()[0] == 1:
            print("   ✅ product_variation_options table exists")
        else:
            print("   ❌ product_variation_options table NOT found!")
            return
        
        # 2. Check table structure
        print("\n2. Checking table structure...")
        cursor.execute("DESCRIBE product_variation_options")
        columns = cursor.fetchall()
        print("   Columns:")
        for col in columns:
            print(f"      - {col[0]} ({col[1]})")
        
        # 3. Check if there are any products
        print("\n3. Checking for existing products...")
        cursor.execute("SELECT id, title, seller_id FROM products LIMIT 5")
        products = cursor.fetchall()
        
        if products:
            print(f"   Found {len(products)} products:")
            for p in products:
                print(f"      - Product ID {p[0]}: {p[1]} (Seller: {p[2]})")
                
                # Check variations for this product
                cursor.execute("""
                    SELECT id, variation_type, variation_value, price_adjustment, stock
                    FROM product_variation_options
                    WHERE product_id = %s
                """, (p[0],))
                variations = cursor.fetchall()
                
                if variations:
                    print(f"        Variations:")
                    for v in variations:
                        print(f"          - {v[1]}: {v[2]} (Price +₱{v[3]}, Stock: {v[4]})")
                else:
                    print(f"        No variations yet")
        else:
            print("   No products found in database")
        
        # 4. Check cart_items table for variation support
        print("\n4. Checking cart_items table...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'cart_items' 
            AND COLUMN_NAME = 'variation_id'
        """, (DB_CONFIG['db'],))
        
        if cursor.fetchone()[0] == 1:
            print("   ✅ cart_items has variation_id column")
        else:
            print("   ❌ cart_items missing variation_id column")
        
        # 5. Check order_items table for variation support
        print("\n5. Checking order_items table...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'order_items' 
            AND COLUMN_NAME = 'variation_id'
        """, (DB_CONFIG['db'],))
        
        if cursor.fetchone()[0] == 1:
            print("   ✅ order_items has variation_id column")
        else:
            print("   ❌ order_items missing variation_id column")
        
        # 6. Check products table for date columns
        print("\n6. Checking products table for food safety columns...")
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'products' 
            AND COLUMN_NAME IN ('manufacture_date', 'expiry_date')
        """, (DB_CONFIG['db'],))
        
        date_cols = [row[0] for row in cursor.fetchall()]
        if 'manufacture_date' in date_cols:
            print("   ✅ products has manufacture_date column")
        else:
            print("   ❌ products missing manufacture_date column")
            
        if 'expiry_date' in date_cols:
            print("   ✅ products has expiry_date column")
        else:
            print("   ❌ products missing expiry_date column")
        
        print("\n" + "="*50)
        print("✅ VARIATION SYSTEM TEST COMPLETE!")
        print("="*50)
        print("\nNext steps:")
        print("  1. Open seller dashboard in browser")
        print("  2. Click 'Add New Product'")
        print("  3. Click 'Add Variation' button")
        print("  4. Fill in variation details")
        print("  5. Save product")
        print("  6. Check browser console (F12) for debug logs")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_variation_system()
